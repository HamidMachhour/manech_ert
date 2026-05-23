<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scan Details - ERT Station</title>
    <link rel="stylesheet" href="{{ asset('css/dashboard.css') }}">
</head>
<body style="background-color: #f4f7f6; padding: 20px;">
    <div class="container">
        <header style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
            <div>
                <h1>Scan Analysis: {{ $scan->profile_line_name }}</h1>
                <p>Project: {{ $scan->project->name }} | Spacing: {{ $scan->electrode_spacing_meters }}m</p>
            </div>
            <div style="display: flex; gap: 10px;">
                <a href="{{ route('projects.index') }}" class="btn" style="background: #6c757d; color: white;">Project Archive</a>
                <a href="{{ route('dashboard') }}" class="btn btn-primary">Back to Dashboard</a>
            </div>
        </header>

        <div class="grid" style="grid-template-columns: 1fr 3fr;">
            <!-- Scan Metadata -->
            <div class="column">
                <div class="card">
                    <h3>Scan Metadata</h3>
                    <div class="form-group">
                        <label>Status</label>
                        <span class="status-badge status-{{ $scan->status }}">
                            {{ strtoupper($scan->status) }}
                        </span>
                    </div>
                    <div class="form-group">
                        <label>Created At</label>
                        <p>{{ $scan->created_at->format('Y-m-d H:i:s') }}</p>
                    </div>
                    <div class="form-group">
                        <label>Total Points</label>
                        <p>{{ $scan->matrixPoints->count() }} readings</p>
                    </div>
                    <div style="margin-top: 20px;">
                        <a href="{{ route('scans.export', $scan->id) }}" class="btn btn-primary" style="width: 100%; text-align: center; display: block;">Export to CSV (RES2DINV)</a>
                    </div>
                </div>
            </div>

            <!-- Data Table -->
            <div class="column">
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3>Matrix Data Explorer</h3>
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <label style="margin: 0; font-size: 0.8em;">Filter Stake A:</label>
                            <input type="number" id="filter-a" style="width: 60px;" placeholder="A">
                            <label style="margin: 0; font-size: 0.8em;">Stake B:</label>
                            <input type="number" id="filter-b" style="width: 60px;" placeholder="B">
                            <button id="apply-filter" class="btn btn-primary" style="padding: 5px 10px; font-size: 0.8em;">Filter</button>
                            <button id="clear-filter" class="btn" style="background: #ccc; padding: 5px 10px; font-size: 0.8em;">Clear</button>
                        </div>
                    </div>
                    <div id="live-log">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>A</th>
                                    <th>B</th>
                                    <th>M</th>
                                    <th>N</th>
                                    <th>V (mV)</th>
                                    <th>I (mA)</th>
                                    <th>Rho (Ωm)</th>
                                </tr>
                            </thead>
                            <tbody id="matrix-body">
                                <!-- Data injected by JS -->
                            </tbody>
                        </table>
                    </div>
                    <div id="pagination-controls" style="margin-top: 15px; display: flex; justify-content: center; gap: 10px;">
                        <!-- Pagination buttons injected by JS -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function loadPoints(page = 1, stakeA = '', stakeB = '') {
            const url = `/scan/{{ $scan->id }}/points?page=${page}&stake_a=${stakeA}&stake_b=${stakeB}`;
            try {
                const response = await fetch(url);
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                // Ensure data.data and pagination info exist
                if (!data.data || !Array.isArray(data.data)) {
                    throw new Error('Invalid response format: missing or invalid data array');
                }
                
                if (typeof data.current_page === 'undefined' || typeof data.last_page === 'undefined') {
                    throw new Error('Invalid response format: missing pagination data');
                }
                
                const body = document.getElementById('matrix-body');
                body.innerHTML = '';
                
                if (data.data.length === 0) {
                    body.innerHTML = '<tr><td colspan="8" style="text-align: center;">No data points found.</td></tr>';
                } else {
                    data.data.forEach(pt => {
                        const row = `<tr>
                            <td>${pt.id}</td>
                            <td>${pt.stake_a}</td>
                            <td>${pt.stake_b}</td>
                            <td>${pt.stake_m}</td>
                            <td>${pt.stake_n}</td>
                            <td>${pt.measured_voltage.toFixed(4)}</td>
                            <td>${pt.injected_current.toFixed(4)}</td>
                            <td><strong>${pt.calculated_apparent_resistivity.toFixed(4)}</strong></td>
                        </tr>`;
                        body.insertAdjacentHTML('beforeend', row);
                    });
                }

                renderPagination(data);
            } catch (error) {
                console.error('Error loading points:', error);
                document.getElementById('matrix-body').innerHTML = `<tr><td colspan="8" style="text-align: center; color: red;">Error loading data: ${error.message}</td></tr>`;
            }
        }

        function renderPagination(data) {
            const container = document.getElementById('pagination-controls');
            container.innerHTML = '';
            
            if (!data || typeof data.current_page === 'undefined') {
                console.error('Invalid pagination data:', data);
                return;
            }
            
            if (data.current_page > 1) {
                const prev = document.createElement('button');
                prev.innerText = 'Previous';
                prev.className = 'btn';
                prev.style.background = '#ddd';
                prev.onclick = () => loadPoints(data.current_page - 1, document.getElementById('filter-a').value, document.getElementById('filter-b').value);
                container.appendChild(prev);
            }

            const span = document.createElement('span');
            span.innerText = `Page ${data.current_page} of ${data.last_page} (${data.total} total)`;
            span.style.fontSize = '0.9em';
            container.appendChild(span);

            if (data.current_page < data.last_page) {
                const next = document.createElement('button');
                next.innerText = 'Next';
                next.className = 'btn';
                next.style.background = '#ddd';
                next.onclick = () => loadPoints(data.current_page + 1, document.getElementById('filter-a').value, document.getElementById('filter-b').value);
                container.appendChild(next);
            }
        }

        document.getElementById('apply-filter').onclick = () => {
            loadPoints(1, document.getElementById('filter-a').value, document.getElementById('filter-b').value);
        };

        document.getElementById('clear-filter').onclick = () => {
            document.getElementById('filter-a').value = '';
            document.getElementById('filter-b').value = '';
            loadPoints(1);
        };

        // Initial load
        loadPoints();
    </script>
</body>
</html>
