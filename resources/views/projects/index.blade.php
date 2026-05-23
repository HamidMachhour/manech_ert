<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Archive - ERT Station</title>
    <link rel="stylesheet" href="{{ asset('css/dashboard.css') }}">
</head>
<body style="background-color: #f4f7f6; padding: 20px;">
    <div class="container">
        <header style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
            <div>
                <h1>Project Archive</h1>
                <p>Historical record of all groundwater scanning projects.</p>
            </div>
            <a href="{{ route('dashboard') }}" class="btn btn-primary">Back to Dashboard</a>
        </header>

        <div class="card">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Project Name</th>
                        <th>Region</th>
                        <th>Coordinates</th>
                        <th>Area (m²)</th>
                        <th>Status</th>
                        <th>Created At</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse($projects as $project)
                        <tr>
                            <td>{{ $project->id }}</td>
                            <td><strong>{{ $project->name }}</strong></td>
                            <td>{{ $project->region_name }}</td>
                            <td>{{ $project->location_coordinates }}</td>
                            <td>{{ $project->total_area_analyzed_sq_meters }}</td>
                            <td>
                                <span class="status-badge {{ $project->status == 'active' ? 'status-running' : 'status-aborted' }}">
                                    {{ $project->status }}
                                </span>
                            </td>
                            <td>{{ $project->created_at->format('Y-m-d H:i') }}</td>
                            <td style="display: flex; gap: 5px;">
                                @if($project->scans->count() > 0)
                                    <a href="{{ route('scans.show', $project->scans->max('id')) }}" class="btn" style="background: #007bff; color: white; padding: 5px 10px; font-size: 0.8em;">Latest Scan</a>
                                @else
                                    <span style="font-size: 0.8em; color: #999;">No scans</span>
                                @endif
                                <a href="{{ route('projects.scans', $project->id) }}" class="btn" style="background: #6c757d; color: white; padding: 5px 10px; font-size: 0.8em;">All Scans</a>
                            </td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="7" style="text-align: center; padding: 20px;">No projects found in the database.</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
