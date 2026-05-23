<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class SystemState extends Model
{
    protected $primaryKey = 'state_key';
    public $incrementing = false;
    protected $keyType = 'string';

    protected $fillable = [
        'state_key',
        'state_value',
    ];
}
