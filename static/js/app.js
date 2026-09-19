function toggleSidebar(){document.getElementById('sidebar')?.classList.toggle('open')}
const fileInput=document.getElementById('fileInput');
if(fileInput){fileInput.addEventListener('change',()=>{document.getElementById('fileName').textContent=fileInput.files[0]?.name||'No file selected'})}
const program=document.getElementById('programSelect'), area=document.getElementById('areaSelect'), req=document.getElementById('reqSelect');
if(program&&area&&req){const filter=()=>{[...req.options].forEach((o,i)=>{if(i===0)return;o.hidden=(!!program.value&&o.dataset.program!==program.value)||(!!area.value&&o.dataset.area!==area.value)});if(req.selectedOptions[0]?.hidden)req.value=''};program.addEventListener('change',filter);area.addEventListener('change',filter);filter()}
setTimeout(()=>document.querySelectorAll('.alert').forEach(a=>a.classList.add('fade')),4500)
