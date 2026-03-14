// =========================
// Load Agents
// =========================

async function loadAgents() {
    try {
        console.log("[DEBUG] Fetching agents...");
        const response = await fetch('/agents');
        
        if (!response.ok) {
            console.error("[ERROR] /agents returned:", response.status);
            return;
        }
        
        const agents = await response.json();
        console.log("[DEBUG] Agents received:", agents);

        const tbody = document.querySelector('#agentsTable tbody');
        if (!tbody) {
            console.error("[ERROR] tbody not found");
            return;
        }

        tbody.innerHTML = '';

        if (!agents || agents.length === 0) {
            console.log("[WARNING] No agents to display");
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No agents connected</td></tr>';
            updateStats(0, 0, 0);
            return;
        }

        // Calculate statistics
        let activeCount = 0;
        let highRiskCount = 0;
        let totalTasks = 0;

        agents.forEach(agent => {
            console.log("[DEBUG] Processing agent:", agent.alias);

            if (agent.status === 'alive' || agent.status === 'online') {
                activeCount++;
            }

            if (agent.risk_level === 'HIGH' || agent.risk_level === 'CRITICAL') {
                highRiskCount++;
            }

            let lastTaskHTML = `<span class="text-muted"><i class="fas fa-minus-circle"></i> No tasks</span>`;

            if (agent.last_task && agent.last_task.cmd) {
                totalTasks++;
                const cmdPreview = agent.last_task.cmd.length > 40 ? 
                    agent.last_task.cmd.substring(0, 40) + '...' : 
                    agent.last_task.cmd;
                
                lastTaskHTML = `
                    <div class="fw-semibold text-info mb-1">
                        <i class="fas fa-terminal"></i> ${cmdPreview}
                    </div>
                    <div>
                        <span class="badge bg-${
                            agent.last_task.status === "done" ? "success" :
                            agent.last_task.status === "sent" ? "primary" :
                            agent.last_task.status === "ack" ? "warning" :
                            "secondary"
                        }">
                            ${agent.last_task.status}
                        </span>
                    </div>
                `;
            }

            const riskColor =
                agent.risk_level === "CRITICAL" ? "danger" :
                agent.risk_level === "HIGH" ? "warning" :
                agent.risk_level === "MEDIUM" ? "info" :
                agent.risk_level === "LOW" ? "secondary" :
                "success";

            const statusIcon = (agent.status === 'alive' || agent.status === 'online') ? 
                '<i class="fas fa-circle text-success"></i>' : 
                '<i class="fas fa-circle text-danger"></i>';

            const hostname   = agent.hostname   || '';
            const ipAddress  = agent.ip_address  || '';
            const osInfo     = agent.os_info      || '';
            const agentUser  = agent.agent_user   || '';

            const identityHtml = (hostname || ipAddress) ? `
                <div class="text-muted" style="font-size:0.78em; margin-top:2px;">
                    ${hostname ? `<i class="fas fa-desktop me-1"></i>${hostname}` : ''}
                    ${hostname && ipAddress ? ' &nbsp;·&nbsp; ' : ''}
                    ${ipAddress ? `<i class="fas fa-network-wired me-1"></i>${ipAddress}` : ''}
                    ${agentUser ? ` &nbsp;·&nbsp; <i class="fas fa-user me-1"></i>${agentUser}` : ''}
                    ${osInfo ? ` &nbsp;·&nbsp; <i class="fas fa-microchip me-1"></i>${osInfo}` : ''}
                </div>` : '';

            const row = `
                <tr class="agent-row" data-alias="${agent.alias}" style="cursor: pointer;">
                    <td>
                        <span class="fw-bold text-info">
                            <i class="fas fa-laptop"></i> ${agent.alias}
                        </span>
                        ${identityHtml}
                    </td>
                    <td>
                        ${statusIcon}
                        <span class="badge bg-${
                            agent.status === 'alive' || agent.status === 'online' ? 'success' : 'danger'
                        }">
                            ${agent.status}
                        </span>
                    </td>
                    <td>
                        <span class="badge bg-${riskColor}">
                            <i class="fas fa-shield-alt"></i> ${agent.risk_level} (${agent.risk_score})
                        </span>
                    </td>
                    <td>
                        <i class="fas fa-clock text-muted"></i> ${agent.last_seen}
                    </td>
                    <td style="max-width: 350px;">
                        ${lastTaskHTML}
                    </td>
                </tr>
            `;

            tbody.innerHTML += row;
        });

        // Update statistics cards
        updateStats(activeCount, highRiskCount, totalTasks);

        console.log("[DEBUG] Agents table updated");

    } catch (error) {
        console.error("[ERROR] Error loading agents:", error);
        const tbody = document.querySelector('#agentsTable tbody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-danger"><i class="fas fa-exclamation-triangle"></i> Error loading agents: ${error.message}</td></tr>`;
        }
    }
}


// =========================
// Update Statistics Cards
// =========================

function updateStats(activeAgents, highRisk, totalTasks) {
    const activeEl = document.getElementById('activeAgentsCount');
    const riskEl = document.getElementById('highRiskCount');
    const tasksEl = document.getElementById('tasksExecutedCount');
    
    if (activeEl) activeEl.textContent = activeAgents;
    if (riskEl) riskEl.textContent = highRisk;
    if (tasksEl) tasksEl.textContent = totalTasks;
}


// =========================
// Load Incidents
// =========================

async function loadIncidents() {
    try {
        console.log("[DEBUG] Fetching incidents...");
        const response = await fetch('/incidents');
        
        if (!response.ok) {
            console.error("[ERROR] /incidents returned:", response.status);
            return;
        }
        
        const incidents = await response.json();
        console.log("[DEBUG] Incidents received:", incidents);

        const tbody = document.querySelector('#incidentsTable tbody');
        if (!tbody) {
            console.error("[ERROR] incidents tbody not found");
            return;
        }

        tbody.innerHTML = '';

        const openIncidents = incidents.filter(i => i.status === "open");

        if (!incidents || openIncidents.length === 0) {
            console.log("[WARNING] No incidents to display");
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted"><i class="fas fa-check-circle text-success"></i> No open incidents</td></tr>';
            updateIncidentsCount(0);
            return;
        }

        updateIncidentsCount(openIncidents.length);

        openIncidents.forEach(incident => {
            console.log("[DEBUG] Processing incident:", incident.incident_id);

            const severityColor =
                incident.severity === "HIGH" ? "danger" :
                incident.severity === "MEDIUM" ? "warning" :
                incident.severity === "LOW" ? "info" :
                "secondary";

            const severityIcon =
                incident.severity === "HIGH" ? "fa-exclamation-circle" :
                incident.severity === "MEDIUM" ? "fa-exclamation-triangle" :
                "fa-info-circle";

            const row = `
                <tr onclick="window.location.href='/incident/${incident.incident_id}'"
                    style="cursor:pointer;" class="hover-highlight">
                    <td>
                        <i class="fas fa-laptop text-info"></i> ${incident.agent_alias}
                    </td>
                    <td>
                        <i class="fas fa-file-alt text-muted"></i> ${incident.type}
                    </td>
                    <td>
                        <span class="badge bg-${severityColor}">
                            <i class="fas ${severityIcon}"></i> ${incident.severity}
                        </span>
                    </td>
                    <td>
                        <span class="badge bg-primary">
                            <i class="fas fa-flag"></i> ${incident.status}
                        </span>
                    </td>
                </tr>
            `;

            tbody.innerHTML += row;
        });

        console.log("[DEBUG] Incidents table updated");

    } catch (error) {
        console.error("[ERROR] Error loading incidents:", error);
        const tbody = document.querySelector('#incidentsTable tbody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-danger"><i class="fas fa-exclamation-triangle"></i> Error loading incidents</td></tr>`;
        }
    }
}

function updateIncidentsCount(count) {
    const incidentsEl = document.getElementById('openIncidentsCount');
    if (incidentsEl) incidentsEl.textContent = count;
}


// =========================
// Click Agent Row
// =========================

document.addEventListener("click", function (event) {
    const row = event.target.closest(".agent-row");

    if (row) {
        const alias = row.dataset.alias;
        console.log("[DEBUG] Navigating to agent:", alias);
        window.location.href = `/agent/${alias}`;
    }
});


// =========================
// Auto Refresh
// =========================

function autoRefresh() {
    console.log("[DEBUG] Auto-refreshing at:", new Date().toLocaleTimeString());
    loadAgents();
    loadIncidents();
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("[DEBUG] Page loaded, loading initial data...");
    autoRefresh();
    setInterval(autoRefresh, 5000);
});
