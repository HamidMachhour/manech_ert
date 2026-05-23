<?php

namespace App\Console\Jobs;

use App\Models\Scan;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Process;
use Illuminate\Support\Facades\Log;

class RunGroundScan implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $scanId,
        public float $spacing
    ) {}

    public function handle(): void
    {
        $scan = Scan::find($this->scanId);
        if (!$scan) {
            Log::error("Scan not found for ID: {$this->scanId}");
            return;
        }

        $scan->update(['status' => 'running']);

        // Execute the Python emulator script using the virtual environment's python executable
        $pythonPath = '/mnt/ssd_kodak/manech_ert/venv/bin/python3';
        
        $result = Process::timeout(3600)->run([
            $pythonPath, 
            '/mnt/ssd_kodak/manech_ert/emulator/matrix_scanner.py', 
            '--scan_id=' . $this->scanId, 
            '--spacing=' . $this->spacing
        ]);

        if ($result->successful()) {
            Log::info("Scan {$this->scanId} completed successfully.");
        } else {
            Log::error("Scan {$this->scanId} failed or was aborted. Output: " . $result->errorOutput());
        }
    }
}
