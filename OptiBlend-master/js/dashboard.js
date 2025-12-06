// OptiCem AI - Logique Tableau de Bord Avancée (Version Pro)
const canvas = document.getElementById('mixChart');
const ctx = canvas.getContext('2d');

// État
let currentData = {
    target: 0,
    predicted: 0,
    stability: 0,
    tsr: 0,
    co2: 0,
    mix: [],
    chem: {
        chlorine: 0,
        moisture: 0
    }
};

// Utilitaires
function randomFloat(min, max) {
    return (Math.random() * (max - min) + min).toFixed(2);
}
function randomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

// Simulation Données
function generateData() {
    const target = randomInt(3800, 4100);
    const variance = randomInt(-30, 30); // Plus précis pour la version pro
    const predicted = target + variance;
    const stability = (97 + Math.random() * 2.5).toFixed(1); // Très stable
    const tsr = randomFloat(60, 80); // Objectifs ambitieux
    const co2 = randomFloat(14, 20);
    const chlorine = randomFloat(0.4, 0.85); // Maitrisé
    const moisture = randomFloat(10, 15);

    let rdf = randomInt(40, 50);
    let tires = randomInt(15, 20);
    let solvants = randomInt(5, 12);
    let biomass = randomInt(8, 15);
    let coal = 100 - (rdf + tires + solvants + biomass);

    const mix = [
        { label: 'RDF (Partenaire A)', value: rdf, color: '#4f46e5' },
        { label: 'Pneus (Partenaire B)', value: tires, color: '#db2777' },
        { label: 'SRF (Interne)', value: solvants, color: '#0d9488' },
        { label: 'Biomasse Cond.', value: biomass, color: '#8b5cf6' },
        { label: 'Fossile (Appoint)', value: coal, color: '#64748b' }
    ];

    return { target, predicted, stability, tsr, co2, mix, chem: { chlorine, moisture } };
}

// Rendu Graphique
function drawChart(data) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;

    // Fond Blanc
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, width, height);

    const padding = 50;
    const barWidth = (width - padding * 2) / data.mix.length - 25;
    const maxValue = 65;
    const chartHeight = height - padding * 2;

    data.mix.forEach((item, index) => {
        const x = padding + index * (barWidth + 20);
        const barHeight = (item.value / maxValue) * chartHeight;
        const y = height - padding - barHeight;

        ctx.fillStyle = 'rgba(0,0,0,0.05)';
        ctx.beginPath();
        ctx.roundRect(x + 5, y + 5, barWidth, barHeight, 8);
        ctx.fill();

        ctx.fillStyle = item.color;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 8);
        ctx.fill();

        ctx.fillStyle = '#475569';
        ctx.font = '500 10px Inter';
        ctx.textAlign = 'center';

        const parts = item.label.match(/(.*)\s\((.*)\)/);
        if (parts) {
            ctx.fillText(parts[1], x + barWidth / 2, height - padding + 20);
            ctx.fillStyle = '#94a3b8';
            ctx.fillText(parts[2], x + barWidth / 2, height - padding + 34);
        } else {
            ctx.fillText(item.label, x + barWidth / 2, height - padding + 20);
        }

        ctx.fillStyle = '#1e293b';
        ctx.font = 'bold 13px Inter';
        ctx.fillText(item.value + '%', x + barWidth / 2, y - 10);
    });
}

// Texte Rapport Expert
function getAnalysisText(data) {
    return `
    SYNTHÈSE STRATÉGIQUE (LOT #904-B) :
    La consolidation des flux provenant de nos partenaires certifiés permet aujourd'hui un point de fonctionnement optimal.
    
    FIABILITÉ DU PROCESS :
    Le mix agrégé délivre un PCI stable de ${data.predicted} kcal/kg (Cible : ${data.target}). L'indice de confiance IA (${data.stability}%) confirme une compatibilité totale avec la courbe de cuisson actuelle.
    
    METRIQUES QUALITÉ & SÉCURITÉ :
    - Volatils (Chlore) : ${data.chem.chlorine}% (Sous seuil critique).
    - Taux d'Humidité : ${data.chem.moisture}% (Excellent séchage).
    
    PERFORMANCE RSE :
    En activant les leviers de l'économie circulaire, nous atteignons un TSR de ${data.tsr}%. Cette substitution intelligente permet d'éviter l'émission de ${data.co2} tonnes de CO2 sur ce cycle horaire.
    `.trim();
}

function updateDashboard() {
    currentData = generateData();

    document.getElementById('pciTarget').textContent = currentData.target;
    document.getElementById('pciPredicted').textContent = currentData.predicted;
    document.getElementById('stabilityIdx').textContent = currentData.stability + '%';

    const tsrEl = document.getElementById('tsrValue');
    if (tsrEl) tsrEl.textContent = currentData.tsr + '%';

    drawChart(currentData);
}

async function exportPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const user = localStorage.getItem('user') || 'Direction Technique';

    // En-tête
    doc.setFillColor(79, 70, 229);
    doc.rect(0, 0, 210, 40, 'F');

    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(22);
    doc.text("OptiCem AI", 20, 25);

    doc.setFontSize(12);
    doc.setFont("helvetica", "normal");
    doc.text("Rapport de Performance Énergétique", 130, 25);

    // Métadonnées
    doc.setTextColor(50, 50, 50);
    doc.setFontSize(10);
    doc.text(`Opérateur : ${user}`, 20, 55);
    doc.text(`Date : ${new Date().toLocaleString('fr-FR')}`, 20, 60);

    doc.setLineWidth(0.5);
    doc.setDrawColor(200);
    doc.line(20, 70, 190, 70);

    const startY = 85;
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("KPIs de Production", 20, 80);

    doc.setFontSize(12);
    doc.setFont("helvetica", "normal");
    doc.text(`PCI Cible : ${currentData.target} kcal/kg`, 20, startY);
    doc.text(`PCI Réalisé : ${currentData.predicted} kcal/kg`, 80, startY);
    doc.text(`Indice Stabilité : ${currentData.stability}%`, 150, startY);
    doc.text(`Taux TSR : ${currentData.tsr}%`, 20, startY + 10);

    // Texte d'Analyse
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("Analyse Stratégique du Mix", 20, startY + 30);

    doc.setFontSize(11);
    doc.setFont("helvetica", "normal");
    const analysis = getAnalysisText(currentData);
    const splitText = doc.splitTextToSize(analysis, 170);
    doc.text(splitText, 20, startY + 40);

    // Graphique
    const imgData = canvas.toDataURL("image/jpeg", 1.0);
    const nextY = startY + 40 + (splitText.length * 5) + 10;
    doc.setDrawColor(0);
    doc.rect(19, nextY - 1, 172, 92);
    doc.addImage(imgData, 'JPEG', 20, nextY, 170, 90);

    // Pied de page
    doc.setFontSize(9);
    doc.setTextColor(150);
    doc.text("Document Confidentiel - Généré par OptiCem AI", 105, 285, { align: 'center' });

    doc.save("Rapport_OptiCem_Pro.pdf");
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    updateDashboard();

    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            const originalHTML = refreshBtn.innerHTML;
            refreshBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Optimisation en cours...';
            setTimeout(() => {
                updateDashboard();
                refreshBtn.innerHTML = originalHTML;
            }, 800);
        });
    }

    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportPDF);
    }

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            localStorage.removeItem('user');
            window.location.href = 'index.html';
        });
    }

    window.addEventListener('resize', () => drawChart(currentData));
});
