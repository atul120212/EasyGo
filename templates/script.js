// ---------------------------
// Function to handle PDF download
// ---------------------------
const handleDownloadPDF = async () => {
  const filename = "travel-itinerary.pdf";
  const element = document.body;

  const downloadBtn = document.getElementById('download-btn');
  downloadBtn.textContent = 'Generating...';
  downloadBtn.disabled = true;

  try {
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      windowWidth: document.documentElement.offsetWidth,
      windowHeight: document.documentElement.offsetHeight,
    });

    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF('p', 'mm', 'a4');

    const imgData = canvas.toDataURL('image/jpeg', 1.0);
    const imgWidth = 210;
    const pageHeight = 297;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    let heightLeft = imgHeight;

    let position = 0;
    pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;

    while (heightLeft >= 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
    }

    pdf.save(filename);
  } catch (error) {
    console.error("Failed to generate PDF:", error);
    alert("Sorry, there was an error generating the PDF.");
  } finally {
    downloadBtn.textContent = 'Download PDF';
    downloadBtn.disabled = false;
  }
};

// ---------------------------
// Function to handle "Start Over"
// ---------------------------
const handleStartOver = () => {
  if (confirm("Are you sure you want to start over? All expenses will be cleared.")) {
    window.location.reload();
  }
};

// ---------------------------
// Expense Tracker logic
// ---------------------------
let form = document.getElementById("expenseForm");
let expenseList = document.getElementById("expenseList");
let totalElement = document.getElementById("total");

if (form) {
  let total = 0;

  form.addEventListener("submit", function (e) {
    e.preventDefault();

    let desc = document.getElementById("expenseDesc").value.trim();
    let amount = parseFloat(document.getElementById("expenseAmount").value);

    if (desc && !isNaN(amount)) {
      total += amount;
      totalElement.innerText = total.toFixed(2);

      // Get current time
      let now = new Date();
      let timeString = now.toLocaleString();

      // Create list item
      let li = document.createElement("li");
      li.innerHTML = `<strong>${desc}</strong> - Rs ${amount.toFixed(2)} <em>(${timeString})</em>`;
      expenseList.appendChild(li);

      form.reset();
    }
  });
}

// ---------------------------
// Add event listeners
// ---------------------------
document.addEventListener('DOMContentLoaded', () => {
  const downloadButton = document.getElementById('download-btn');
  const startOverButton = document.getElementById('start-over-btn');

  if (downloadButton) {
    downloadButton.addEventListener('click', handleDownloadPDF);
  }
  if (startOverButton) {
    startOverButton.addEventListener('click', handleStartOver);
  }
});
