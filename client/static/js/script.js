document.addEventListener('DOMContentLoaded', function () {
  // Elementos DOM
  const dropArea = document.getElementById('dropArea');
  const fileInput = document.getElementById('fileInput');
  const browseBtn = document.getElementById('browseBtn');
  const fileList = document.getElementById('fileList');
  const processBtn = document.getElementById('processBtn');
  const clearBtn = document.getElementById('clearBtn');
  const resultsSection = document.getElementById('resultsSection');
  const resultsBody = document.getElementById('resultsBody');
  const exportBtn = document.getElementById('exportBtn');
  const loading = document.getElementById('loading');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');

  // Array para armazenar os arquivos selecionados
  let selectedFiles = [];

  // Event Listeners
  browseBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', handleFileSelect);
  processBtn.addEventListener('click', processFiles);
  clearBtn.addEventListener('click', clearFiles);
  exportBtn.addEventListener('click', exportToCSV);

  // Drag and Drop
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach((eventName) => {
    dropArea.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ['dragenter', 'dragover'].forEach((eventName) => {
    dropArea.addEventListener(eventName, highlight, false);
  });

  ['dragleave', 'drop'].forEach((eventName) => {
    dropArea.addEventListener(eventName, unhighlight, false);
  });

  function highlight() {
    dropArea.classList.add('highlight');
  }

  function unhighlight() {
    dropArea.classList.remove('highlight');
  }

  dropArea.addEventListener('drop', handleDrop, false);

  function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
  }

  function handleFileSelect(e) {
    const files = e.target.files;
    handleFiles(files);
  }

  function handleFiles(files) {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      // Verificar se é um PDF
      if (file.type === 'application/pdf') {
        // Verificar se o arquivo já foi adicionado
        if (!selectedFiles.some((f) => f.name === file.name && f.size === file.size)) {
          selectedFiles.push(file);
        }
      } else {
        alert(`O arquivo "${file.name}" não é um PDF válido. Apenas arquivos PDF são aceitos.`);
      }
    }
    updateFileList();
  }

  function updateFileList() {
    fileList.innerHTML = '';

    if (selectedFiles.length === 0) {
      processBtn.disabled = true;
      clearBtn.disabled = true;
      return;
    }

    processBtn.disabled = false;
    clearBtn.disabled = false;

    selectedFiles.forEach((file, index) => {
      const fileItem = document.createElement('div');
      fileItem.className = 'file-item';

      const fileName = document.createElement('div');
      fileName.className = 'file-name';
      fileName.textContent = file.name;

      const fileSize = document.createElement('div');
      fileSize.className = 'file-size';
      fileSize.textContent = formatFileSize(file.size);

      const fileRemove = document.createElement('div');
      fileRemove.className = 'file-remove';
      fileRemove.textContent = '✕';
      fileRemove.addEventListener('click', () => {
        selectedFiles.splice(index, 1);
        updateFileList();
      });

      fileItem.appendChild(fileName);
      fileItem.appendChild(fileSize);
      fileItem.appendChild(fileRemove);

      fileList.appendChild(fileItem);
    });
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function clearFiles() {
    selectedFiles = [];
    updateFileList();
    fileInput.value = '';
    resultsSection.style.display = 'none';
    progressBar.style.width = `0%`;
    progressContainer.style.display = `none`;
    progressText.textContent = ``;
  }

  async function processFiles() {
    if (selectedFiles.length === 0) return;

    // Mostrar loading
    loading.style.display = 'block';
    progressContainer.style.display = 'block';
    processBtn.disabled = true;
    clearBtn.disabled = true;

    // Limpar resultados anteriores
    resultsBody.innerHTML = '';
    resultsSection.style.display = 'none';

    // Processar arquivos
    const totalFiles = selectedFiles.length;
    let processedFiles = 0;

    for (const file of selectedFiles) {
      const formData = new FormData();

      formData.append('files', file);

      // Atualizar progresso
      processedFiles++;
      const progress = (processedFiles / totalFiles) * 100;
      progressBar.style.width = `${progress}%`;
      progressText.textContent = `Processando ${processedFiles} de ${totalFiles} arquivos`;

      try {
        const response = await fetch('https://extractor-numeric-codebar.onrender.com/api/extract-barcodes', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();

        const { filename, barcode, barcode_found } = data.results[0];

        // Adicionar linha na tabela de resultados
        const row = document.createElement('tr');

        const fileNameCell = document.createElement('td');
        fileNameCell.textContent = filename;

        const barcodeCell = document.createElement('td');
        barcodeCell.textContent = barcode || 'N/A';

        const statusCell = document.createElement('td');
        statusCell.textContent = barcode_found ? 'Encontrado' : 'Não encontrado';
        statusCell.className = barcode_found ? 'status-success' : 'status-error';

        row.appendChild(fileNameCell);
        row.appendChild(barcodeCell);
        row.appendChild(statusCell);

        resultsBody.appendChild(row);
      } catch (error) {
        console.error(`Erro ao processar ${file.name}:`, error);

        // Adicionar linha de erro
        const row = document.createElement('tr');

        const fileNameCell = document.createElement('td');
        fileNameCell.textContent = file.name;

        const barcodeCell = document.createElement('td');
        barcodeCell.textContent = 'Erro no processamento';

        const statusCell = document.createElement('td');
        statusCell.textContent = 'Erro';
        statusCell.className = 'status-error';

        row.appendChild(fileNameCell);
        row.appendChild(barcodeCell);
        row.appendChild(statusCell);

        resultsBody.appendChild(row);
      }
    }

    // Esconder loading e mostrar resultados
    loading.style.display = 'none';
    resultsSection.style.display = 'block';
    processBtn.disabled = false;
    clearBtn.disabled = false;
    fileList.innerHTML = '';
    selectedFiles = [];
  }

  // Função simulada de processamento (substituir pela chamada real à API)
  function simulateProcessing(file) {
    return new Promise((resolve) => {
      // Simular tempo de processamento
      setTimeout(() => {
        // Simular resultados aleatórios para demonstração
        const hasBarcode = Math.random() > 0.3;
        const barcode = hasBarcode ? generateRandomBarcode() : null;
        const status = hasBarcode ? 'Encontrado' : 'Não encontrado';

        resolve({
          filename: file.name,
          barcode: barcode,
          status: status,
        });
      }, 1500 + Math.random() * 2000); // Tempo aleatório entre 1.5 e 3.5 segundos
    });
  }

  // Gerar código de barras aleatório para demonstração
  function generateRandomBarcode() {
    const parts = [];
    for (let i = 0; i < 4; i++) {
      let part = '';
      for (let j = 0; j < 5; j++) {
        part += Math.floor(Math.random() * 10);
      }
      parts.push(part);
    }
    return parts.join('');
  }

  function exportToCSV() {
    const rows = [];
    const headers = ['Arquivo', 'Codigo_de_Barras', 'Status'];
    rows.push(headers.join(';'));

    const tableRows = resultsBody.querySelectorAll('tr');

    tableRows.forEach((row) => {
      const cells = row.querySelectorAll('td');
      const rowData = Array.from(cells).map((cell, i) => (i === 1 ? '="' + cell.textContent + '"' : cell.textContent));
      rows.push(rowData.join(';'));
    });

    const csvContent = rows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    console.log(blob);
    const url = URL.createObjectURL(blob);
    console.log(url);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'codigos_barras.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
});
