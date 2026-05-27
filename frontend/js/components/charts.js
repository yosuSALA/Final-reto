// SVG charts (donut + scatter)
export function renderClaimsScatter(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container || !data || !data.series) return;
    const series = data.series;
    const W = Math.max(800, series.length * 28);
    const H = 220;
    const padL = 44, padR = 18, padT = 18, padB = 38;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const maxY = Math.max(1, ...series.map(p => p.count));
    const stepX = series.length > 1 ? innerW / (series.length - 1) : 0;
    const yScale = c => padT + innerH - (c / maxY) * innerH;

    const yTicks = [];
    const tickCount = Math.min(5, maxY);
    for (let i = 0; i <= tickCount; i++) {
        const v = Math.round((maxY * i) / tickCount);
        yTicks.push({ v, y: yScale(v) });
    }

    const linePath = series.map((p, i) => {
        const x = padL + i * stepX;
        const y = yScale(p.count);
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");

    const dots = series.map((p, i) => {
        const x = padL + i * stepX;
        const y = yScale(p.count);
        const r = p.count === 0 ? 3 : Math.min(9, 4 + p.count * 1.5);
        const color = p.count === 0 ? "#cbd5e1" : p.count >= 3 ? "#ef4444" : p.count >= 2 ? "#f59e0b" : "#6366f1";
        return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r}" fill="${color}" opacity="0.85" stroke="white" stroke-width="1.5"><title>${p.date}: ${p.count} siniestro${p.count !== 1 ? 's' : ''}</title></circle>`;
    }).join("");

    const xLabels = series.map((p, i) => {
        if (series.length > 15 && i % Math.ceil(series.length / 10) !== 0 && i !== series.length - 1) return "";
        const x = padL + i * stepX;
        const d = p.date.slice(5);
        return `<text x="${x.toFixed(1)}" y="${H - padB + 16}" text-anchor="middle" font-size="10" fill="#64748b" font-family="Inter">${d}</text>`;
    }).join("");

    const yGrid = yTicks.map(t => `
        <line x1="${padL}" y1="${t.y}" x2="${W - padR}" y2="${t.y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="2,3"/>
        <text x="${padL - 8}" y="${t.y + 3}" text-anchor="end" font-size="10" fill="#64748b" font-family="Inter">${t.v}</text>
    `).join("");

    container.innerHTML = `
        <svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="display:block;">
            ${yGrid}
            <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${H - padB}" stroke="#94a3b8" stroke-width="1"/>
            <line x1="${padL}" y1="${H - padB}" x2="${W - padR}" y2="${H - padB}" stroke="#94a3b8" stroke-width="1"/>
            <path d="${linePath}" fill="none" stroke="#6366f1" stroke-width="1.5" opacity="0.4"/>
            ${dots}
            ${xLabels}
            <text x="${padL}" y="${padT - 4}" font-size="10" fill="#64748b" font-family="Inter" font-weight="600">Siniestros / día</text>
        </svg>
        <div style="display:flex; gap:14px; padding:8px 12px; font-size:0.8rem; color:var(--text-muted); flex-wrap:wrap;">
            <span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#cbd5e1;margin-right:4px;"></span>0</span>
            <span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#6366f1;margin-right:4px;"></span>1</span>
            <span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#f59e0b;margin-right:4px;"></span>2</span>
            <span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ef4444;margin-right:4px;"></span>3+</span>
        </div>
    `;
}

export function renderDonut(containerId, legendId, data) {
    const container = document.getElementById(containerId);
    const legend = document.getElementById(legendId);
    if (!container || !legend) return;
    const total = data.critical + data.warning + data.clean;
    if (total === 0) {
        container.innerHTML = '<div class="empty-state"><h3>Sin datos</h3></div>';
        return;
    }
    const items = [
        { label: "Critico", value: data.critical, color: "#ef4444" },
        { label: "Advertencia", value: data.warning, color: "#f59e0b" },
        { label: "Limpio", value: data.clean, color: "#10b981" },
    ];
    const size = 180, cx = 90, cy = 90, r = 70, sw = 24;
    const circumference = 2 * Math.PI * r;
    let offset = 0;
    let paths = "";
    items.forEach(item => {
        if (item.value === 0) return;
        const pct = item.value / total;
        const dash = pct * circumference;
        const gap = circumference - dash;
        paths += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${item.color}" stroke-width="${sw}" stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${-offset}" stroke-linecap="round" opacity="0.85"/>`;
        offset += dash;
    });
    container.innerHTML = `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(0,0,0,0.04)" stroke-width="${sw}"/>${paths}<text x="${cx}" y="${cy - 6}" text-anchor="middle" fill="#0f172a" font-size="28" font-weight="800" font-family="Inter">${total}</text><text x="${cx}" y="${cy + 14}" text-anchor="middle" fill="#64748b" font-size="10" font-weight="600" font-family="Inter" text-transform="uppercase">FACTURAS</text></svg>`;
    legend.innerHTML = items.map(i => `<div class="donut-legend-item"><div class="donut-legend-dot" style="background:${i.color}"></div><span>${i.label}: <strong>${i.value}</strong></span></div>`).join("");
}
