<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('matrix_points', function (Blueprint $table) {
            $table->id();
            $table->foreignId('scan_id')->constrained()->onDelete('cascade');
            $table->integer('stake_a');
            $table->integer('stake_b');
            $table->integer('stake_m');
            $table->integer('stake_n');
            $table->double('measured_voltage', 15, 8);
            $table->double('injected_current', 15, 8);
            $table->double('calculated_apparent_resistivity', 15, 8);
            $table->timestamp('timestamp')->useCurrent();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('matrix_points');
    }
};
