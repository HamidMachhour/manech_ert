<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('system_states', function (Blueprint $table) {
            $table->string('state_key')->primary();
            $table->text('state_value');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('system_states');
    }
};
