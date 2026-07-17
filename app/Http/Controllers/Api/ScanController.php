<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Project;
use App\Models\Scan;
use App\Models\MatrixPoint;
use App\Models\SystemState;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Symfony\Component\Process\Process as SymfonyProcess;

class ScanController extends Controller
{
    public function index(): mixed
    {
        $projects = Project::orderBy('created_at', 'desc')->get();
        
        if (request()->expectsJson()) {
            return response()->json($projects);
        }

        return view('projects.index', compact('projects'));
    }

    public function listScans($projectId): mixed
    {
        $project = Project::findOrFail($projectId);
        $scans = $project->scans()->orderBy('created_at', 'desc')->get();

        return view('projects.scans', compact('project', 'scans'));
    }

    /**
     * Show a specific scan and its matrix points.
     */
    public function showScan($id): mixed
    {
        $scan = Scan::with(['project', 'matrixPoints'])->findOrFail($id);
        
        if (request()->expectsJson()) {
            return response()->json($scan);
        }

        return view('scans.show', compact('scan'));
    }

    public function listMatrixPoints(Request $request, $scanId): mixed
    {
        $query = MatrixPoint::where('scan_id', $scanId);

        // Filtering by electrode pairs (only if values are provided)
        if ($request->filled('stake_a')) {
            $query->where('stake_a', $request->stake_a);
        }
        if ($request->filled('stake_b')) {
            $query->where('stake_b', $request->stake_b);
        }

        $points = $query->orderBy('id', 'asc')->paginate(100);

        return response()->json($points);
    }

    public function exportScanCsv($scanId): \Symfony\Component\HttpFoundation\Response
    {
        $scan = Scan::findOrFail($scanId);
        $points = MatrixPoint::where('scan_id', $scanId)->orderBy('id', 'asc')->get();

        $callback = function() use ($points) {
            $file = fopen('php://output', 'w');
            fputcsv($file, ['ID', 'A', 'B', 'M', 'N', 'Voltage', 'Current', 'Resistivity']);

            foreach ($points as $point) {
                fputcsv($file, [
                    $point->id, $point->stake_a, $point->stake_b, 
                    $point->stake_m, $point->stake_n, 
                    $point->measured_voltage, $point->injected_current, 
                    $point->calculated_apparent_resistivity
                ]);
            }
            fclose($file);
        };

        return response()->streamDownload($callback, "scan_{$scanId}_export.csv", [
            'Content-Type' => 'text/csv',
        ]);
    }

    /**
     * Create a new project with location metadata.
     */
    public function storeProject(Request $request): \Illuminate\Http\Response|\Illuminate\Http\JsonResponse
// ...existing code...
    {
        try {
            $validated = $request->validate([
                'name' => 'required|string',
                'location_coordinates' => 'required|string',
                'region_name' => 'required|string',
                'total_area_analyzed_sq_meters' => 'nullable|numeric',
                'soil_type_notes' => 'nullable|string',
            ]);

            $project = Project::create($validated);

            if ($request->expectsJson()) {
                return response()->json($project, 201);
            }

            return redirect()->route('dashboard')->with('success', 'Project created successfully! ID: ' . $project->id);
        } catch (\Exception $e) {
            if ($request->expectsJson()) {
                return response()->json(['error' => $e->getMessage()], 500);
            }
            return redirect()->back()->withErrors(['error' => $e->getMessage()]);
        }
    }

 
    /**
     * Initialize a new scan and dispatch the background worker.
     */
    public function startScan(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'project_id' => 'required|exists:projects,id',
            'profile_line_name' => 'required|string',
            'electrode_spacing_meters' => 'required|numeric',
        ]);

        // 1. Reset the abort flag in system_states
        SystemState::updateOrCreate(
            ['state_key' => 'kill_signal_active'],
            ['state_value' => '0']
        );

        // 2. Create the scan record
        $scan = Scan::create([
            'project_id' => $validated['project_id'],
            'profile_line_name' => $validated['profile_line_name'],
            'electrode_spacing_meters' => $validated['electrode_spacing_meters'],
            'status' => 'pending',
        ]);

        // 3. Launch the scanner directly in the background so the dashboard sees the
        // scan as running immediately, without depending on the queue worker.
        try {
            $projectRoot = '/var/www/manech_ert';
            $pythonPath = $projectRoot . '/venv/bin/python3';
            $scannerScript = $projectRoot . '/emulator/matrix_scanner.py';
            $logPath = storage_path('logs/scan_' . $scan->id . '.log');

            $shellCommand = sprintf(
                'cd %s && source %s/venv/bin/activate && %s %s --scan_id=%d --spacing=%.10f > %s 2>&1',
                escapeshellarg($projectRoot),
                escapeshellarg($projectRoot),
                escapeshellarg($pythonPath),
                escapeshellarg($scannerScript),
                $scan->id,
                (float) $validated['electrode_spacing_meters'],
                escapeshellarg($logPath)
            );

            $process = new SymfonyProcess(['/bin/bash', '-lc', $shellCommand], $projectRoot);
            $process->setEnv([
                'PATH' => '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:' . $projectRoot . '/venv/bin',
                'HOME' => '/var/www/manech_ert',
                'USER' => 'www-data',
                'SHELL' => '/bin/bash',
            ]);
            $process->setTimeout(1);
            $process->start();

            $scan->update(['status' => 'running']);
        } catch (\Throwable $e) {
            Log::error('Failed to launch scan process', [
                'scan_id' => $scan->id,
                'error' => $e->getMessage(),
            ]);
            $scan->update(['status' => 'failed']);

            return response()->json([
                'message' => 'Scan start failed',
                'error' => $e->getMessage(),
            ], 500);
        }

        // Also ensure the shared-memory abort flag is cleared for the new scan
        $shmPath = '/dev/shm/scan_aborted';
        try {
            @file_put_contents($shmPath, '0');
            @chmod($shmPath, 0666);
        } catch (\Throwable $e) {
            // non-fatal: proceed but log in real deployments if desired
        }

        return response()->json([
            'message' => 'Scan initiated successfully',
            'scan_id' => $scan->id
        ], 202);
    }

    /**
     * Trigger an emergency abort by flipping the state flag.
     */
    public function abortScan(): JsonResponse
    {
        // mark the DB state
        SystemState::updateOrCreate(
            ['state_key' => 'kill_signal_active'],
            ['state_value' => '1']
        );

        // Write the shared-memory abort flag so external processes see it immediately
        $shmPath = '/dev/shm/scan_aborted';
        try {
            @file_put_contents($shmPath, '1');
            @chmod($shmPath, 0666);
        } catch (\Throwable $e) {
            // non-fatal
        }

        // Optionally update the currently running scan row (if any)
        try {
            $running = Scan::where('status', 'running')->latest('updated_at')->first();
            if ($running) {
                $running->update(['status' => 'aborted']);
            }
        } catch (\Throwable $e) {
            // ignore
        }

        return response()->json([
            'message' => 'Emergency abort signal sent to hardware controller'
        ]);
    }

    /**
     * Get live project data, current scan status, and recorded points.
     */
    public function getLiveProjectData($projectId): mixed
    {
        try {
            $project = Project::with(['scans' => function($query) {
                $query->latest();
            }])->findOrFail($projectId);

            $latestScan = $project->scans->first();
            $points = [];

            if ($latestScan) {
                $points = \App\Models\MatrixPoint::where('scan_id', $latestScan->id)
                    ->orderBy('timestamp', 'asc')
                    ->get();
            }

            return response()->json([
                'project' => $project,
                'current_scan' => $latestScan,
                'matrix_points' => $points,
            ]);
        } catch (\Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    public function destroyScan($id): mixed
    {
        $scan = Scan::findOrFail($id);
        $scan->delete();

        if (request()->expectsJson()) {
            return response()->json(['message' => 'Scan deleted successfully'], 200);
        }

        return redirect()->back()->with('success', 'Scan deleted successfully');
    }
}
