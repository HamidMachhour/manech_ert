<?php

namespace App\Console\Jobs;

use App\Models\Scan;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;
use Symfony\Component\Process\Process as SymfonyProcess;

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
        $projectRoot = '/var/www/manech_ert'; // Adjust this path as necessary
        $pythonPath = $projectRoot . '/venv/bin/python3';
        $scannerScript = $projectRoot . '/emulator/matrix_scanner.py';

        // Ensure shared memory flag exists and is writable by both web/worker users
        $shmPath = '/dev/shm/scan_aborted';
        if (!file_exists($shmPath)) {
            @file_put_contents($shmPath, '0');
            @chmod($shmPath, 0666);
        }

        // Launch the Python process as the orangepi user so it uses the same hardware
        // permissions as the working CLI run.
        $shellCommand = sprintf(
            '/usr/bin/sudo -n -u orangepi -H %s %s --scan_id=%d --spacing=%.10f',
            escapeshellarg($pythonPath),
            escapeshellarg($scannerScript),
            $this->scanId,
            $this->spacing
        );

        $process = new SymfonyProcess(['/bin/bash', '-lc', $shellCommand], $projectRoot);
        $process->setEnv([
            'PATH' => getenv('PATH') ?: '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
            'HOME' => getenv('HOME') ?: $projectRoot,
        ]);
        $process->setTimeout(3600);
        $process->start();

        // Poll loop: check abort file while process runs
        while ($process->isRunning()) {
            if ($this->handleAbortSignal($shmPath)) {
                // Attempt graceful stop
                try {
                    $process->stop(1);
                } catch (\Throwable $e) {
                    Log::warning("Failed to stop process for scan {$this->scanId}: {$e->getMessage()}");
                }

                Log::info("Scan {$this->scanId} aborted via shared memory signal.");
                $scan->update(['status' => 'aborted']);
                break;
            }

            // Small sleep to avoid busy looping (200ms)
            usleep(200000);
        }

        // If process finished naturally, record result
        if (!$process->isRunning()) {
            if ($process->getExitCode() === 0) {
                Log::info("Scan {$this->scanId} completed successfully.");
                $scan->update(['status' => 'completed']);
            } else {
                Log::error("Scan {$this->scanId} failed or was aborted. ExitCode: " . $process->getExitCode() . ", Output: " . $process->getErrorOutput());
                if ($scan->status !== 'aborted') {
                    $scan->update(['status' => 'failed']);
                }
            }
        }
    }

    /**
     * Check the shared memory abort flag.
     * Returns true if abort signal is active (file contains '1').
     */
    private function handleAbortSignal(string $shmPath): bool
    {
        try {
            if (!file_exists($shmPath)) {
                return false;
            }

            $state = @file_get_contents($shmPath);
            if ($state === false) {
                return false;
            }

            return trim($state) === '1';
        } catch (\Throwable $e) {
            Log::warning("Shared memory read failed: {$e->getMessage()}");
            return false;
        }
    }
}
