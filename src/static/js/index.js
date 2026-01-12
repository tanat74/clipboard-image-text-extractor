const resultsP = document.querySelector("#results");
const statusP = document.querySelector("#status");
const copyBtn = document.querySelector("#copy");
const languageSelect = document.querySelector("#language");
const processedImage = document.querySelector("#processedImage");

const originalBtnText = copyBtn.innerText;
let currentImageData = null;

document.addEventListener("paste", (event) => {
  try {
    statusP.innerText = "Processing image...";
    copyBtn.style.display = "none";
    processedImage.style.display = "none";

    const items = (event.clipboardData || event.originalEvent.clipboardData)
      .items;

    let processed = false;
    for (let index in items) {
      const item = items[index];
      if (item.kind === "file") {
        const blob = item.getAsFile();
        const reader = new FileReader();
        reader.onload = async (event) => {
          currentImageData = event.target.result;
          await extractText(currentImageData);
        };
        reader.readAsDataURL(blob);
        processed = true;
        break;
      }
    }

    if (!processed) {
      statusP.innerText =
        "Bad request: No image found in clipboard. Paste another image to process it.";
    } else {
      copyBtn.style.display = "block";
    }
  } catch (error) {
    statusP.innerText = `Client error: ${error}. Paste another image to process it.`;
  }
});

async function extractText(base64data) {
  const language = languageSelect.value;
  const res = await fetch("/results", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: "data=" + encodeURIComponent(base64data) + "&language=" + encodeURIComponent(language),
  });

  const data = await res.text();

  if (!res.ok) {
    statusP.innerText = `${data}. Paste another image to process it.`;
    return;
  }

  statusP.innerText = "Image processed! Paste another image to process it.";
  resultsP.value = data;
  
  // Display the processed image
  processedImage.src = currentImageData;
  processedImage.style.display = "block";
}

// Re-process image when language changes
languageSelect.addEventListener("change", async () => {
  if (currentImageData) {
    statusP.innerText = "Processing image...";
    await extractText(currentImageData);
  }
});

copyBtn.addEventListener("click", () => {
  copyBtn.innerText = originalBtnText;

  navigator.clipboard.writeText(resultsP.value);

  copyBtn.innerText = "Text copied!";
  setTimeout(() => {
    copyBtn.innerText = originalBtnText;
  }, 3000);
});
