const API_BASE = "/api";
const STORAGE_KEY = "scholarship-session";

function getSession() {
	try {
		return JSON.parse(localStorage.getItem(STORAGE_KEY)) || null;
	} catch {
		return null;
	}
}

function setSession(user) {
	localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

function clearSession() {
	localStorage.removeItem(STORAGE_KEY);
}

function formatPercent(value) {
	return `${Number(value).toFixed(1)}%`;
}

function truncateText(text, limit = 180) {
	const normalized = String(text || "").replace(/\s+/g, " ").trim();
	if (normalized.length <= limit) {
		return normalized;
	}
	return `${normalized.slice(0, limit - 1).trim()}…`;
}

async function apiRequest(path, options = {}) {
	const response = await fetch(`${API_BASE}${path}`, {
		headers: {
			"Content-Type": "application/json",
			...(options.headers || {}),
		},
		...options,
	});

	const contentType = response.headers.get("content-type") || "";
	const data = contentType.includes("application/json") ? await response.json() : await response.text();

	if (!response.ok) {
		const message = typeof data === "string" ? data : data.message || "Request failed.";
		throw new Error(message);
	}

	return data;
}

function logout() {
	clearSession();
	window.location.href = "index.html";
}

function bindLogoutButton() {
	const button = document.getElementById("logout-button");
	if (button) {
		button.addEventListener("click", logout);
	}
}

function initLoginPage() {
	const form = document.getElementById("login-form");
	if (!form) return;

	const toggleButtons = document.querySelectorAll("[data-toggle-panel]");
	toggleButtons.forEach((button) => {
		button.addEventListener("click", () => {
			const panelId = button.getAttribute("data-toggle-panel");
			const panel = document.getElementById(panelId);
			if (panel) {
				panel.classList.toggle("hidden");
			}
		});
	});

	form.addEventListener("submit", async (event) => {
		event.preventDefault();
		const message = document.getElementById("login-message");
		const formData = new FormData(form);
		const payload = Object.fromEntries(formData.entries());

		try {
			const response = await apiRequest("/auth/login", {
				method: "POST",
				body: JSON.stringify(payload),
			});
			setSession(response.user);
			message.textContent = response.message;
			message.className = "message success";
			window.location.href = response.user.role === "admin" ? "admin.html" : "dashboard.html";
		} catch (error) {
			message.textContent = error.message;
			message.className = "message error";
		}
	});

	// verification UI removed; only forgot-password remains

	const resetRequestForm = document.getElementById("reset-request-form");
	if (resetRequestForm) {
		resetRequestForm.addEventListener("submit", async (event) => {
			event.preventDefault();
			const message = document.getElementById("reset-request-message");
			const payload = Object.fromEntries(new FormData(resetRequestForm).entries());
			try {
				const response = await apiRequest("/auth/request-password-reset", {
					method: "POST",
					body: JSON.stringify(payload),
				});
				message.textContent = response.message;
				message.className = "message success";
			} catch (error) {
				message.textContent = error.message;
				message.className = "message error";
			}
		});
	}

	const resetForm = document.getElementById("reset-form");
	if (resetForm) {
		resetForm.addEventListener("submit", async (event) => {
			event.preventDefault();
			const message = document.getElementById("reset-message");
			const payload = Object.fromEntries(new FormData(resetForm).entries());
			try {
				const response = await apiRequest("/auth/reset-password", {
					method: "POST",
					body: JSON.stringify(payload),
				});
				message.textContent = response.message;
				message.className = "message success";
			} catch (error) {
				message.textContent = error.message;
				message.className = "message error";
			}
		});
	}
}

function initRegisterPage() {
	const form = document.getElementById("register-form");
	if (!form) return;

	form.addEventListener("submit", async (event) => {
		event.preventDefault();
		const message = document.getElementById("register-message");
		const formData = new FormData(form);
		const payload = Object.fromEntries(formData.entries());
		payload.role = "student";

		try {
			const response = await apiRequest("/auth/register", {
				method: "POST",
				body: JSON.stringify(payload),
			});
			message.textContent = response.message;
			message.className = "message success";
			window.location.href = "login.html";
		} catch (error) {
			message.textContent = error.message;
			message.className = "message error";
		}
	});
}

function renderApplications(listElement, applications) {
	if (!applications.length) {
		listElement.innerHTML = '<div class="empty-state">No applications submitted yet.</div>';
		return;
	}

	listElement.innerHTML = applications.map((application) => `
		<article class="list-card">
			<div class="list-header">
				<strong>${application.full_name}</strong>
				<span class="pill ${application.status === "Approved" ? "pill-success" : application.status === "Rejected" ? "pill-danger" : "pill-warning"}">${application.status}</span>
			</div>
			<p>${application.eligibility_prediction} · ${formatPercent(application.eligibility_probability * 100)}</p>
			<small>${truncateText(application.eligibility_explanation, 170)}</small>
		</article>
	`).join("");
}

function renderStudentSummary(applications) {
	const totalElement = document.getElementById("student-total");
	const latestStatusElement = document.getElementById("student-latest-status");
	const averageElement = document.getElementById("student-average");
	if (!totalElement || !latestStatusElement || !averageElement) {
		return;
	}

	totalElement.textContent = applications.length;
	latestStatusElement.textContent = applications[0]?.status || "-";
	const averageProbability = applications.length
		? applications.reduce((sum, application) => sum + Number(application.eligibility_probability || 0), 0) / applications.length
		: 0;
	averageElement.textContent = formatPercent(averageProbability * 100);
}

async function initStudentDashboard() {
	const form = document.getElementById("application-form");
	const list = document.getElementById("applications-list");
	if (!form || !list) return;

	const session = getSession();
	if (!session) {
		window.location.href = "login.html";
		return;
	}
	if (session.role !== "student") {
		window.location.href = "admin.html";
		return;
	}

	document.getElementById("student-greeting").textContent = `Welcome, ${session.name}`;
	form.elements.full_name.value = session.name;
	form.elements.email.value = session.email;
	bindLogoutButton();

	async function loadApplications() {
		const data = await apiRequest(`/applications?user_id=${session.id}&role=student`);
		const applications = data.applications || [];
		renderApplications(list, applications);
		renderStudentSummary(applications);
	}

	form.addEventListener("submit", async (event) => {
		event.preventDefault();
		const message = document.getElementById("application-message");
		const resultTitle = document.getElementById("result-title");
		const resultProbability = document.getElementById("result-probability");
		const resultExplanation = document.getElementById("result-explanation");
		const formData = new FormData(form);
		const payload = Object.fromEntries(formData.entries());
		payload.user_id = session.id;
		payload.previous_scholarship = form.elements.previous_scholarship.checked ? 1 : 0;
		payload.extracurricular = form.elements.extracurricular.checked ? 1 : 0;

		try {
			const response = await apiRequest("/applications", {
				method: "POST",
				body: JSON.stringify(payload),
			});

			resultTitle.textContent = response.prediction.prediction;
			resultProbability.textContent = `Probability: ${formatPercent(response.prediction.probability * 100)}`;
			resultExplanation.textContent = response.explanation;
			message.textContent = response.message;
			message.className = "message success";
			form.reset();
			form.elements.full_name.value = session.name;
			form.elements.email.value = session.email;
			await loadApplications();
		} catch (error) {
			message.textContent = error.message;
			message.className = "message error";
		}
	});

	await loadApplications();
}

function renderAdminSummary(summary) {
	document.getElementById("metric-total").textContent = summary.total_applications || 0;
	document.getElementById("metric-approved").textContent = summary.approved || 0;
	document.getElementById("metric-rejected").textContent = summary.rejected || 0;
	document.getElementById("metric-average").textContent = formatPercent((summary.average_probability || 0) * 100);
}

function renderAdminQueue(tbody, applications) {
	if (!applications.length) {
		tbody.innerHTML = '<tr><td colspan="5">No applications available.</td></tr>';
		return;
	}

	tbody.innerHTML = applications.map((application) => `
		<tr>
			<td>
				<strong>${application.full_name}</strong><br>
				<small>${application.category.toUpperCase()} · GPA ${application.gpa}</small>
			</td>
			<td>${application.eligibility_prediction}</td>
			<td>${formatPercent(application.eligibility_probability * 100)}</td>
			<td><span class="pill ${application.status === "Approved" ? "pill-success" : application.status === "Rejected" ? "pill-danger" : "pill-warning"}">${application.status}</span></td>
			<td>
				<div class="action-stack">
					<button class="button success small" data-action="approve" data-id="${application.id}">Approve</button>
					<button class="button danger small" data-action="reject" data-id="${application.id}">Reject</button>
					<input class="review-note" data-note-for="${application.id}" type="text" placeholder="Reviewer note">
				</div>
			</td>
		</tr>
	`).join("");
}

async function initAdminDashboard() {
	const queue = document.getElementById("review-queue");
	const insights = document.getElementById("insights-list");
	if (!queue || !insights) return;

	const session = getSession();
	if (!session) {
		window.location.href = "login.html";
		return;
	}
	if (session.role !== "admin") {
		window.location.href = "dashboard.html";
		return;
	}

	document.getElementById("admin-greeting").textContent = `Logged in as ${session.name}`;
	bindLogoutButton();

	async function refreshDashboard() {
		const summary = await apiRequest("/dashboard/summary");
		const applicationsData = await apiRequest("/applications?role=admin");
		const insightsData = await apiRequest("/reports/insights");

		renderAdminSummary(summary);
		renderAdminQueue(queue, applicationsData.applications || []);

		insights.innerHTML = (insightsData.insights || []).map((item) => `
			<article class="list-card">
				<small>${item}</small>
			</article>
		`).join("") || '<div class="empty-state">No reports generated yet.</div>';
	}

	queue.addEventListener("click", async (event) => {
		const button = event.target.closest("button[data-action]");
		if (!button) return;

		const applicationId = button.dataset.id;
		const action = button.dataset.action;
		const noteField = document.querySelector(`[data-note-for="${applicationId}"]`);

		try {
			await apiRequest(`/applications/${applicationId}/review`, {
				method: "PATCH",
				body: JSON.stringify({
					status: action === "approve" ? "Approved" : "Rejected",
					reviewer_note: noteField ? noteField.value : "",
					reviewed_by: session.id,
				}),
			});
			await refreshDashboard();
		} catch (error) {
			alert(error.message);
		}
	});

	await refreshDashboard();
}

document.addEventListener("DOMContentLoaded", () => {
	initLoginPage();
	initRegisterPage();
	initStudentDashboard();
	initAdminDashboard();
});
