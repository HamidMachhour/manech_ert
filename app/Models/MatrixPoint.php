<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class MatrixPoint extends Model
{
    use HasFactory;

    public $timestamps = false;

    protected $fillable = [
        'scan_id',
        'stake_a',
        'stake_b',
        'stake_m',
        'stake_n',
        'measured_voltage',
        'injected_current',
        'calculated_apparent_resistivity',
        'timestamp',
    ];

    public function scan(): BelongsTo
    {
        return $this->belongsTo(Scan::class);
    }
}
