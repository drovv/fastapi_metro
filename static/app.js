const form = document.getElementById("route-form");
const fromInput = document.getElementById("from-station");
const toInput = document.getElementById("to-station");
const statusBox = document.getElementById("status");
const resultBox = document.getElementById("result");
const summaryBox = document.getElementById("summary");
const routeListBox = document.getElementById("route-list");
const stationsList = document.getElementById("stations-list");
const swapButton = document.getElementById("swap-button");
const exampleButtons = document.querySelectorAll(".example-button");

function setStatus(message, type = "neutral") {
    statusBox.textContent = message;
    statusBox.className = `status status--${type}`;
}

function setLoading(isLoading) {
    const submitButton = form.querySelector(".submit-button");
    submitButton.disabled = isLoading;
    submitButton.textContent = isLoading ? "Считаем..." : "Найти маршрут";
}

function fillStations(stations) {
    stationsList.innerHTML = "";

    for (const item of stations) {
        const option = document.createElement("option");
        option.value = item.station_name;
        option.label = item.lines.join(", ");
        stationsList.appendChild(option);
    }
}

function badgeClass(moveType) {
    if (moveType === "transfer") {
        return "route-badge route-badge--transfer";
    }

    if (moveType === "start") {
        return "route-badge route-badge--start";
    }

    return "route-badge route-badge--train";
}

function badgeText(step) {
    if (step.move_type === "start") {
        return "Старт";
    }

    if (step.move_type === "transfer") {
        return `Переход ${step.minutes_from_previous} мин`;
    }

    return `Поезд ${step.minutes_from_previous} мин`;
}

function renderSummary(route) {
    summaryBox.innerHTML = `
        <article class="summary-card">
            <span>Время в пути</span>
            <strong>${route.total_minutes} мин</strong>
        </article>
        <article class="summary-card">
            <span>Станций в маршруте</span>
            <strong>${route.stations_in_path}</strong>
        </article>
        <article class="summary-card">
            <span>Переходов</span>
            <strong>${route.transfers_count}</strong>
        </article>
    `;
}

function renderRoute(route) {
    routeListBox.innerHTML = "";

    for (const step of route.path) {
        const article = document.createElement("article");
        article.className = "route-step";

        article.innerHTML = `
            <div class="route-step__dot" style="background:#${step.line_color};"></div>
            <div>
                <h3 class="route-step__title">${step.station_name}</h3>
                <p class="route-step__meta">${step.line_name}</p>
            </div>
            <div class="${badgeClass(step.move_type)}">${badgeText(step)}</div>
        `;

        routeListBox.appendChild(article);
    }
}

async function loadStations() {
    try {
        const response = await fetch("/stations");
        const data = await response.json();

        fillStations(data.stations);
        setStatus(`Список станций загружен: ${data.count} названий.`, "success");
    } catch (error) {
        setStatus("Не удалось загрузить список станций.", "error");
    }
}

async function loadRoute(fromStation, toStation) {
    setLoading(true);
    setStatus("Ищем кратчайший путь...", "neutral");
    resultBox.classList.add("hidden");

    const params = new URLSearchParams({
        from_station: fromStation,
        to_station: toStation,
    });

    try {
        const response = await fetch(`/route?${params.toString()}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Ошибка при поиске маршрута");
        }

        renderSummary(data);
        renderRoute(data);
        resultBox.classList.remove("hidden");
        setStatus(`Маршрут найден: ${data.from_station} → ${data.to_station}.`, "success");
    } catch (error) {
        setStatus(error.message, "error");
    } finally {
        setLoading(false);
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const fromStation = fromInput.value.trim();
    const toStation = toInput.value.trim();

    if (!fromStation || !toStation) {
        setStatus("Введите обе станции.", "error");
        return;
    }

    await loadRoute(fromStation, toStation);
});

swapButton.addEventListener("click", () => {
    const currentFrom = fromInput.value;
    fromInput.value = toInput.value;
    toInput.value = currentFrom;
});

for (const button of exampleButtons) {
    button.addEventListener("click", async () => {
        fromInput.value = button.dataset.from;
        toInput.value = button.dataset.to;
        await loadRoute(button.dataset.from, button.dataset.to);
    });
}

loadStations();
