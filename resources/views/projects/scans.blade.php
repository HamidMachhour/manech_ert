<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Scans - ERT Station</title>
    <link rel="stylesheet" href="{{ asset('css/dashboard.css') }}">
</head>
<body style="background-color: #f4f7f6; padding: 20px;">
    <div class="container">
        <header style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
            <div>
                <h1>Scans for {{ $project->name }}</h1>
                <p>Manage and review all electrical resistivity runs for this project.</p>
            </div>
            <a href="{{ route('projects.index') }}" class="btn" style="background: #6c757d; color: white;">Back to Projects</a>
        </header>

        <div class="card">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Profile Line</th>
                        <th>Spacing (m)</th>
                        <th>Status</th>
                        <th>Created At</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse($scans as $scan)
                        <tr style="{{ $scan->status == 'running' ? 'background-color: #fffdf0;' : '' }}">
                            <td>{{ $scan->id }}</td>
                            <td>{{ $scan->profile_line_name }}</td>
                            <td>{{ $scan->electrode_spacing_meters }}</td>
                            <td>
                                <span class="status-badge status-{{ $scan->status }}">
                                    {{ strtoupper($scan->status) }}
                                </span>
                            </td>
                            <td>{{ $scan->created_at->format('Y-m-d H:i') }}</td>
                            <td style="display: flex; gap: 5px;">
                                <a href="{{ route('scans.show', $scan->id) }}" class="btn" style="background: #007bff; color: white; padding: 5px 10px; font-size: 0.8em;">View Data</a>
                                <form action="{{ route('scans.destroy', $scan->id) }}" method="POST" onsubmit="return confirm('Are you sure you want to delete this scan? All matrix points will be lost.');">
                                    @csrf
                                    @method('DELETE')
                                    <button type="submit" class="btn" style="background: #dc3545; color: white; padding: 5px 10px; font-size: 0.8em;">Delete</button>
                                </form>
                            </td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="6" style="text-align: center; padding: 20px;">No scans recorded for this project.</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
