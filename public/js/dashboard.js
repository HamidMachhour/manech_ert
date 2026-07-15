document.addEventListener('DOMContentLoaded', () => {
    let currentProjectId = null;
    let pollingInterval = null;

    const elements = {
        projectForm: document.getElementById('project-form'),
        scanForm: document.getElementById('scan-form'),
        startBtn: document.getElementById('start-btn'),
        abortBtn: document.getElementById('abort-btn'),
        statusText: document.getElementById('status-text'),
        progressText: document.getElementById('progress-text'),
        logTableBody: document.getElementById('log-table-body'),
        projectSelect: document.getElementById('project-select')
    };

    // Initialize Project
    elements.projectForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(elements.projectForm);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/projects', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify(data)
            });
            const project = await response.json();
            alert('Project created successfully!');
            // Refresh page to populate the new project in the select dropdown
            window.location.reload();
        } catch (error) {
            console.error('Error creating project:', error);
        }
    });

    // Start Scan
    elements.scanForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const currentProjectId = elements.projectSelect.value;
        if (!currentProjectId) return alert('Please select a project first');

        const formData = new FormData(elements.scanForm);
        const data = Object.fromEntries(formData.entries());
        data.project_id = currentProjectId;

        try {
            const response = await fetch('/scan/start', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify(data)
            });
            if (response.status === 202) {
                startPolling();
                elements.startBtn.disabled = true;
            }
        } catch (error) {
            console.error('Error starting scan:', error);
        }
    });

    // Emergency Abort
    elements.abortBtn.addEventListener('click', async () => {
        try {
            await fetch('/scan/abort', { 
                method: 'POST',
                headers: { 
                    'Accept': 'application/json',
                    'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
                }
            });
            alert('Abort signal sent!');
        } catch (error) {
            console.error('Error aborting scan:', error);
        }
    });

    function startPolling() {
        if (pollingInterval) clearInterval(pollingInterval);
        pollingInterval = setInterval(updateDashboard, 1000);
    }

    async function updateDashboard() {
        const currentProjectId = elements.projectSelect.value;
        if (!currentProjectId) return;

        try {
            const response = await fetch(`/scan/live/${currentProjectId}`, {
                headers: { 
                    'Accept': 'application/json'
                }
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            
            const scan = data.current_scan;
            if (!scan) return;

            // Update Status
            elements.statusText.innerText = scan.status.toUpperCase();
            elements.statusText.className = `status-badge status-${scan.status}`;

            // Update Progress
            const pointsCount = data.matrix_points.length;
            elements.progressText.innerText = `Recorded ${pointsCount} matrix points...`;

            // Update Table
            elements.logTableBody.innerHTML = '';
            data.matrix_points.slice().reverse().forEach(pt => {
                const row = `<tr>
                    <td>${pt.stake_a}</td>
                    <td>${pt.stake_b}</td>
                    <td>${pt.stake_m}</td>
                    <td>${pt.stake_n}</td>
                    <td>${pt.measured_voltage.toFixed(4)}</td>
                    <td>${pt.injected_current.toFixed(4)}</td>
                    <td>${pt.calculated_apparent_resistivity.toFixed(4)}</td>
                </tr>`;
                elements.logTableBody.insertAdjacentHTML('beforeend', row);
            });

            // --- BUTTON STATE MANAGEMENT ---
            if (scan.status === 'running') {
                elements.startBtn.disabled = true;
            } else if (scan.status === 'completed' || scan.status === 'aborted') {
                elements.startBtn.disabled = false;
                if (scan.status === 'completed' || scan.status === 'aborted') {
                    // We don't clear interval here anymore so the UI stays updated 
                    // until the user selects a different project or starts a new scan.
                }
            } else {
                // Pending or other states
                elements.startBtn.disabled = false;
            }

        } catch (error) {
            console.error('Polling error:', error);
        }
    }
});
