<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Project extends Model
{
    use HasFactory;

    protected $fillable = [
        'name',
        'location_coordinates',
        'region_name',
        'total_area_analyzed_sq_meters',
        'soil_type_notes',
        'status',
    ];

    public function scans(): HasMany
    {
        return $this->hasMany(Scan::class);
    }
}
