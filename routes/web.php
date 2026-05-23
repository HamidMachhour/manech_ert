<?php

use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('dashboard');
})->name('dashboard');

Route::get('/projects', [App\Http\Controllers\Api\ScanController::class, 'index'])->name('projects.index');
Route::post('/projects', [App\Http\Controllers\Api\ScanController::class, 'storeProject'])->name('projects.store');
Route::get('/projects/{project}/scans', [App\Http\Controllers\Api\ScanController::class, 'listScans'])->name('projects.scans');
Route::delete('/scan/{id}', [App\Http\Controllers\Api\ScanController::class, 'destroyScan'])->name('scans.destroy');
Route::get('/scan/{id}', [App\Http\Controllers\Api\ScanController::class, 'showScan'])->name('scans.show');
Route::get('/scan/{id}/points', [App\Http\Controllers\Api\ScanController::class, 'listMatrixPoints'])->name('scans.points');
Route::get('/scan/{id}/export', [App\Http\Controllers\Api\ScanController::class, 'exportScanCsv'])->name('scans.export');
Route::post('/scan/start', [App\Http\Controllers\Api\ScanController::class, 'startScan']);
Route::post('/scan/abort', [App\Http\Controllers\Api\ScanController::class, 'abortScan']);
Route::get('/scan/live/{projectId}', [App\Http\Controllers\Api\ScanController::class, 'getLiveProjectData']);
