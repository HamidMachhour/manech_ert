<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>ERT Groundwater Scanning Station</title>
    <link rel="stylesheet" href="{{ asset('css/dashboard.css') }}">
</head>
<body>
    <div class="container">
        <header>
            <h1>ERT Geophysical Scanning Station</h1>
            <p>Hardware Emulation & Control Dashboard</p>
        </header>

        <div class="grid">
            <!-- Control Panel -->
            <div class="column">
                <div class="card">
                    <h3>1. Project Initialization</h3>
                    <form id="project-form" >
                        <div class="form-group">
                            <label>Project Name</label>
                            <input type="text" name="name" required placeholder="e.g. North Basin Survey">
                        </div>
                        <div class="form-group">
                            <label>Coordinates (Lat/Long)</label>
                            <input type="text" name="location_coordinates" required placeholder="34.0331, -5.0000">
                        </div>
                        <div class="form-group">
                            <label>Region</label>
                            <input type="text" name="region_name" required placeholder="Fès Region">
                        </div>
                        <div class="form-group">
                            <label>Area (sq meters)</label>
                            <input type="number" name="total_area_analyzed_sq_meters">
                        </div>
                        <div class="form-group">
                            <label>Soil Notes</label>
                            <textarea name="soil_type_notes"></textarea>
                        </div>
                        <button type="submit" class="btn btn-primary">Create Project</button>
                    </form>
                    <div style="margin-top: 15px; text-align: right;">
                        <a href="{{ route('projects.index') }}" class="btn" style="background: #6c757d; color: white;">View Project Archive →</a>
                    </div>
                </div>

                <div class="card">
                    <h3>2. Scan Configuration</h3>
                    <form id="scan-form">
                        <div class="form-group">
                            <label>Select Project</label>
                            <select id="project-select" name="project_id" required>
                                <option value="">-- Select an Active Project --</option>
                                @foreach(\App\Models\Project::where('status', 'active')->get() as $project)
                                    <option value="{{ $project->id }}">{{ $project->name }} (ID: {{ $project->id }})</option>
                                @endforeach
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Profile Line Name</label>
                            <input type="text" name="profile_line_name" required placeholder="Line A - North Grid">
                        </div>
                        <div class="form-group">
                            <label>Electrode Spacing (m)</label>
                            <input type="number" step="0.1" name="electrode_spacing_meters" required value="1.0">
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <button type="submit" id="start-btn" class="btn btn-primary">START SCAN</button>
                            <button type="button" id="abort-btn" class="btn btn-danger" disabled>EMERGENCY ABORT</button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Live Monitoring -->
            <div class="column">
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3>Live Data Stream</h3>
                        <div>
                            Status: <span id="status-text" class="status-badge">IDLE</span>
                        </div>
                    </div>
                    <p id="progress-text">No active scan.</p>
                    
                    <div id="live-log">
                        <table class="data-table" id="log-table">
                            <thead>
                                <tr>
                                    <th>A</th><th>B</th><th>M</th><th>N</th><th>V (mV)</th><th>I (mA)</th><th>Rho (Ωm)</th>
                                </tr>
                            </thead>
                            <tbody id="log-table-body">
                                <!-- Data injected by JS -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="{{ asset('js/dashboard.js') }}"></script>
</body>
</html>
