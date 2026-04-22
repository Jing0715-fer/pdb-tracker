#!/usr/bin/env python3
"""PDB Tracker Web UI — generates JS file at startup to avoid Python string escaping."""

from pathlib import Path
from flask import Flask, request, jsonify, Response, send_file
import re, sqlite3, os, time, json, logging

app = Flask(__name__)
WIKI_PATH = Path("/Users/lijing/Documents/my note/LLM Wiki")
DB_PATH = WIKI_PATH / "data" / "pdb_tracker.db"
REPORTS_DIR = WIKI_PATH / "wiki" / "pdb_weekly_report"
SCRIPT_DIR = Path("/tmp/pdb_scripts")
SCRIPT_DIR.mkdir(exist_ok=True)

# ─── Generate JS file at startup ───────────────────────────────────────────
def write_js():
    NL = "\n"
    lines = []

    def L(s):
        lines.append(s + NL)

    L("(function(){")
    L('"use strict";')
    L("var allEntries=[];var snapshots=[];var allReports=[];var activeWeek=null;var activeEvalMdReport=null;")
    L("var activeMethod='all';var activeSearch='';var sortCol='release_date';var sortAsc=false;")
    L("var activeTab='summary';var activeReport=null;var molViewer=null;")

    L("function escHtml(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;');}")
    L("function fmtMethod(m){if(!m)return '-';if(/electron microscopy|cryo/i.test(m))return 'Cryo-EM';if(/x-ray/i.test(m))return 'X-ray';if(/nmr/i.test(m))return 'NMR';return m;}")

    L("async function init(){try{snapshots=await fetch('/api/snapshots').then(function(r){return r.json();});}catch(e){snapshots=[];}renderWeeks();try{allReports=await fetch('/api/reports/list').then(function(r){return r.json();});}catch(e){allReports=[];}renderReportList(allReports);await loadEntries();}")

    L("function renderWeeks(){var list=document.getElementById('week-list');if(!snapshots||!snapshots.length){list.innerHTML='<div class=\"report-empty\">No data</div>';return;}var sel=document.getElementById('sel-week');sel.innerHTML=\"<option value='all'>All Weeks</option>\";list.innerHTML='';snapshots.forEach(function(s){var card=document.createElement('div');card.className='report-item';card.dataset.wid=s.week_id;card.innerHTML=\"<div class='rname' style='font-size:11px;'><span style='font-family:var(--mono);color:var(--accent);'>\"+s.week_id+\"</span> <span style='font-size:9px;color:var(--muted);'>\"+s.total_structures+\" entries</span></div><div class='rtitle' style='font-size:10px;'>\"+s.week_start+\" -> \"+s.week_end+\"</div><div class='rdate' style='font-size:9px;color:var(--muted);'>EM:\"+(s.cryoem_count||0)+\" | XR:\"+(s.xray_count||0)+\"</div>\";card.onclick=(function(wid,c){return function(){onWeekClick(wid,c);};})(s.week_id,card);list.appendChild(card);var opt=document.createElement('option');opt.value=s.week_id;opt.textContent=s.week_id+' ('+s.week_start+')';sel.appendChild(opt);});}")

    L(r"async function onWeekClick(weekId,card){console.log('onWeekClick called with weekId=',weekId);activeWeek=weekId;activeMethod='all';activeSearch='';document.getElementById('sel-method').value='all';document.getElementById('inp-search').value='';var list=document.getElementById('week-list');var weekCards=list.querySelectorAll('.report-item');var selectedCard=null;if(weekId===null){weekCards.forEach(function(c){c.style.display='';c.classList.remove('active');});document.getElementById('sel-week').value='all';await loadEntries();var oldReportsDiv=document.getElementById('week-reports');if(oldReportsDiv)oldReportsDiv.remove();document.getElementById('back-button-container').style.display='none';}else{weekCards.forEach(function(c){if(c.dataset.wid===weekId){c.classList.add('active');c.style.display='';selectedCard=c;}else{c.classList.remove('active');c.style.display='none';}});if(selectedCard&&selectedCard!==list.firstChild){list.insertBefore(selectedCard,list.firstChild);}document.getElementById('sel-week').value=weekId;await loadEntries();var snap=null;for(var j=0;j<snapshots.length;j++)if(snapshots[j].week_id===weekId){snap=snapshots[j];break;}var filteredReports=[];if(snap){filteredReports=allReports.filter(function(r){var m=r.name.match(/(\d{4}-\d{2}-\d{2})/);return m&&m[1]>=snap.week_start&&m[1]<=snap.week_end;});}var oldReportsDiv=document.getElementById('week-reports');if(oldReportsDiv)oldReportsDiv.remove();var reportsDiv=document.createElement('div');reportsDiv.id='week-reports';reportsDiv.className='week-reports';reportsDiv.style.cssText='padding:8px 10px;border-top:1px solid var(--border);background:var(--card);margin-top:4px;';if(selectedCard){selectedCard.insertAdjacentElement('afterend',reportsDiv);}renderReportListInDiv(filteredReports,reportsDiv);document.getElementById('back-button-container').style.display='block';}}")

    L("async function loadEntries(){var params=[];if(activeWeek!==null)params.push('week='+encodeURIComponent(activeWeek));if(activeMethod!=='all')params.push('method='+encodeURIComponent(activeMethod));if(activeSearch)params.push('q='+encodeURIComponent(activeSearch));params.push('limit=500');var url='/api/entries?'+params.join('&');try{allEntries=await fetch(url).then(function(r){return r.json();});}catch(e){allEntries=[];}var sortedRows=sortEntries(allEntries.slice());for(var si=0;si<sortedRows.length;si++){sortedRows[si]._origIdx=allEntries.indexOf(sortedRows[si]);}renderTable(sortedRows);}")

    L("function sortEntries(arr){return arr.slice().sort(function(a,b){var av=a[sortCol],bv=b[sortCol];var an=parseFloat(av),bn=parseFloat(bv);var aNum=(av!=null&&String(av).trim()!==''&&!isNaN(an));var bNum=(bv!=null&&String(bv).trim()!==''&&!isNaN(bn));var cmp;if(aNum&&bNum){cmp=an-bn;}else if(aNum){cmp=-1;}else if(bNum){cmp=1;}else{cmp=String(av||'').localeCompare(String(bv||''));}return sortAsc?cmp:-cmp;});}")

    L("function renderTable(rows){var tbody=document.getElementById('table-body');tbody.removeAttribute('data-eval-table');document.getElementById('entry-count').textContent=rows.length+' entries';if(!rows.length){tbody.innerHTML=\"<tr><td colspan='7'><div class='preview-empty'><div class='preview-empty-icon'>&#128269;</div>No entries</div></td></tr>\";return;}var html=[];for(var i=0;i<rows.length;i++){var e=rows[i];var origIdx=e._origIdx!=null?e._origIdx:i;var method=e.method||'';var bClass='badge-oth',mLabel=method;if(/electron microscopy|cryo/i.test(method)){bClass='badge-em';mLabel='Cryo-EM';}else if(/x-ray/i.test(method)){bClass='badge-xr';mLabel='X-ray';}else if(/nmr/i.test(method)){bClass='badge-nmr';mLabel='NMR';}var res=e.resolution;var rClass='res-mid',rStr='-';if(res!=null&&String(res).trim()!==''&&!isNaN(parseFloat(res))){var rn=parseFloat(res);rClass=rn<=2.0?'res-good':rn>3.5?'res-poor':'res-mid';rStr=String(res);}var ifTier=e.if_tier||'';var tierBadge=ifTier?\"<span class='if-badge tier-\"+ifTier+\"'>\"+ifTier.toUpperCase()+\"</span>\":'';var ifVal=(e.journal_if!=null&&String(e.journal_if).trim()!=='')?\" <span class='if-val'>IF \"+Number(e.journal_if).toFixed(1)+\"</span>\":'';var ligand=(e.ligand_info||e.ligand||'').trim();var ligs=ligand?(ligand.split(/;/).map(function(l){return l.trim();}).filter(Boolean)):[];var ligHtml='-';if(ligs.length){var chips=[];for(var li=0;li<ligs.length;li++){chips.push(\"<span class='lig-chip' data-lig='\"+escHtml(ligs[li])+\"' data-idx='\"+origIdx+\"'>\"+escHtml(ligs[li])+\"</span>\");}if(ligs.length>maxShow){chips.push(\"<span style='color:var(--muted);font-size:9px;margin-left:4px;'>+\"+(ligs.length-maxShow)+\" more</span>\");}ligHtml=chips.join('');}html.push(\"<tr><td><span class='pdb-link' data-idx='\"+origIdx+\"' data-pdb='\"+escHtml(e.pdb_id)+\"'>\"+escHtml(e.pdb_id)+\"</span></td>\"+\"<td><span class='method-badge \"+bClass+\"'>\"+escHtml(mLabel)+\"</span></td>\"+\"<td><span class='res \"+rClass+\"'>\"+(rStr!=='-'?rStr+' A':'-')+\"</span></td>\"+\"<td>\"+tierBadge+ifVal+\"</td>\"+\"<td class='title-cell' title='\"+escHtml(e.title||'')+\"'>\"+escHtml(e.title||'-')+\"</td>\"+\"<td>\"+(e.release_date||'-')+\"</td>\"+\"<td class='lig-cell'>\"+ligHtml+\"</td></tr>\");}tbody.innerHTML=html.join('');}")

    L("document.getElementById('table-head').onclick=function(e){var th=e.target.closest('th');if(!th||!th.dataset.col)return;var col=th.dataset.col;if(sortCol===col){sortAsc=!sortAsc;}else{sortCol=col;sortAsc=false;}document.querySelectorAll('#table-head th').forEach(function(t){t.dataset.sorted='false';var a=t.querySelector('.sort-arrow');if(a)a.innerHTML='&#8645;';});th.dataset.sorted='true';var sa=th.querySelector('.sort-arrow');if(sa)sa.innerHTML=sortAsc?'&#8593;':'&#8595;';if(currentMode==='eval'){var sorted=sortEvalStructures(currentEvalStructures.slice());currentEvalStructures=sorted;renderEvalTable(sorted);}else{renderTable(sortEntries(allEntries.slice()));}};")

    L("var ttPdb=document.getElementById('tt-pdb');")
    L("document.getElementById('table-body').addEventListener('mouseover',function(e){var pdbSpan=e.target.closest('.pdb-link');if(pdbSpan){var idx=parseInt(pdbSpan.getAttribute('data-idx'),10);var tbody=document.getElementById('table-body');var isEval=tbody&&tbody.getAttribute('data-eval-table')==='true';var entry=isEval?(currentEvalStructures.find(function(s){return s._origIdx===idx;})||{}):(allEntries[idx]||{});if(!entry)return;document.getElementById('tt-pdb-header').textContent=entry.pdb_id;document.getElementById('tt-pdb-method').textContent=fmtMethod(entry.method);document.getElementById('tt-pdb-res').textContent=(entry.resolution!=null)?entry.resolution+' A':'-';document.getElementById('tt-pdb-date').textContent=entry.release_date||'-';document.getElementById('tt-pdb-journal').textContent=entry.journal||'-';document.getElementById('tt-pdb-if').textContent=(entry.journal_if!=null)?Number(entry.journal_if).toFixed(1):'-';var ligs=((entry.ligand_info||entry.ligand||'').trim())?((entry.ligand_info||entry.ligand)||'').replace(/;/g,', '):'-';document.getElementById('tt-pdb-ligs').textContent=ligs;var titleEl=document.getElementById('tt-pdb-title');if(entry.title){titleEl.textContent=entry.title;titleEl.style.display='block';}else{titleEl.style.display='none';}var img=document.getElementById('tt-pdb-img');img.src='https://cdn.rcsb.org/images/structures/'+(entry.pdb_id||'').toLowerCase()+'_assembly-1.jpeg';img.style.display='block';img.onerror=function(){this.style.display='none';};var rect=pdbSpan.getBoundingClientRect();var x=rect.right+14,y=rect.top;if(x+230>window.innerWidth)x=rect.left-244;if(y+360>window.innerHeight)y=window.innerHeight-365;ttPdb.style.left=x+'px';ttPdb.style.top=y+'px';ttPdb.classList.add('show');ttLig.classList.remove('show');return;}var chip=e.target.closest('.lig-chip');if(chip){var ligCode=chip.getAttribute('data-lig');if(!ligCode)return;document.getElementById('tt-lig-header').textContent=ligCode;document.getElementById('tt-lig-name').textContent='Loading...';document.getElementById('tt-lig-name').style.display='block';var img=document.getElementById('tt-lig-img');img.style.display='none';img.onerror=function(){};var firstChar=ligCode.charAt(0);img.src='https://cdn.rcsb.org/images/ccd/labeled/'+firstChar+'/'+ligCode+'.svg';img.onload=function(){img.style.display='block';};img.onerror=function(){img.src='https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/'+encodeURIComponent(ligCode)+'/PNG';img.onload=function(){img.style.display='block';};img.onerror=function(){img.src='https://www.rcsb.org/ligand/graphics/'+ligCode+'-full.png';img.onload=function(){img.style.display='block';};img.onerror=function(){img.style.display='none';};};};fetch('/api/ligand/'+encodeURIComponent(ligCode)).then(function(r){return r.json();}).then(function(d){document.getElementById('tt-lig-name').textContent=d.name||ligCode;}).catch(function(){document.getElementById('tt-lig-name').textContent=ligCode;});var rect=chip.getBoundingClientRect();var x=rect.right+10,y=rect.top-20;if(x+200>window.innerWidth)x=rect.left-210;if(y+200>window.innerHeight)y=window.innerHeight-205;ttLig.style.left=x+'px';ttLig.style.top=y+'px';ttLig.classList.add('show');ttPdb.classList.remove('show');}});")
    L("document.getElementById('table-body').addEventListener('mouseout',function(e){if(e.relatedTarget&&ttPdb.contains(e.relatedTarget))return;if(!e.target.closest('.pdb-link'))return;ttPdb.classList.remove('show');if(e.relatedTarget&&ttLig.contains(e.relatedTarget))return;if(!e.target.closest('.lig-chip'))return;ttLig.classList.remove('show');});")
    L("ttPdb.onmouseenter=function(){ttPdb.classList.add('show');};ttPdb.onmouseleave=function(){ttPdb.classList.remove('show');};")

    L("document.getElementById('table-body').onclick=function(e){var ligChip=e.target.closest('.lig-chip');if(ligChip){var ligCode=ligChip.getAttribute('data-lig');if(ligCode)window.open('https://www.rcsb.org/ligand/'+encodeURIComponent(ligCode),'_blank');return;}var pdbSpan=e.target.closest('.pdb-link');if(pdbSpan){var pdbId=pdbSpan.getAttribute('data-pdb');if(pdbId)window.open('https://www.rcsb.org/structure/'+pdbId.toLowerCase(),'_blank');return;}};")

    L("var ttLig=document.getElementById('tt-lig');")
    L("ttLig.onmouseenter=function(){ttLig.classList.add('show');};ttLig.onmouseleave=function(){ttLig.classList.remove('show');};")

    L("function switchTab(tab){activeTab=tab;document.querySelectorAll('.preview-tab').forEach(function(t){t.classList.toggle('active',t.getAttribute('data-tab')===tab);});document.getElementById('preview-content').style.display='block';if(currentMode==='eval'){if(tab==='summary')showEvalSummary();else if(tab==='report')showEvalFullReport();}else{if(tab==='summary')showSummary(findSnap(activeReport));else if(tab==='report')showFullReport(activeReport);}}")

    L("function findSnap(name){if(!name||!snapshots||!snapshots.length)return null;var m=name.match(/(\\d{4}-\\d{2}-\\d{2})/);if(!m)return null;var d=m[1];for(var i=0;i<snapshots.length;i++){var s=snapshots[i];if(s.week_start<=d&&s.week_end>=d)return s;}return null;}")

    L("function showSummary(snap){var c=document.getElementById('preview-content');if(!snap){c.innerHTML=\"<div class='preview-empty'><div class='preview-empty-icon'>&#128200;</div>No data</div>\";return;}var emRes=snap.cryoem_avg_res||'-';var xrRes=snap.xray_avg_res||'-';c.innerHTML=\"<div class='report-meta'>\"+\"<div class='mr'><span class='ml'>Week</span><span class='mv'>\"+snap.week_id+\"</span></div>\"+\"<div class='mr'><span class='ml'>Period</span><span class='mv'>\"+snap.week_start+\" -> \"+snap.week_end+\"</span></div>\"+\"<div class='mr'><span class='ml'>Total</span><span class='mv'>\"+(snap.total_structures||0)+\"</span></div>\"+\"<div class='mr'><span class='ml'>Cryo-EM</span><span class='mv' style='color:var(--primary)'>\"+(snap.cryoem_count||0)+\" <span style='color:var(--muted)'>(Avg:\"+emRes+\" A)</span></span></div>\"+\"<div class='mr'><span class='ml'>X-ray</span><span class='mv' style='color:var(--secondary)'>\"+(snap.xray_count||0)+\" <span style='color:var(--muted)'>(Avg:\"+xrRes+\" A)</span></span></div>\"+\"</div>\";} ")

    L("function showFullReport(name){if(!name)return;var c=document.getElementById('preview-content');c.innerHTML=\"<div class='preview-empty'><div class='preview-empty-icon'>&#8987;</div>Loading...</div>\";fetch('/api/report?name='+encodeURIComponent(name)).then(function(res){return res.text();}).then(function(md){c.innerHTML=\"<div class='md-content'>\"+renderMD(md)+\"</div>\";}).catch(function(){c.innerHTML=\"<div class='preview-empty'><div class='preview-empty-icon'>&#9888;</div>Failed</div>\";});}")

    L("function onReportClick(name,item){activeReport=name;document.querySelectorAll('.report-item').forEach(function(i){i.classList.remove('active');});item.classList.add('active');document.getElementById('preview-panel').classList.remove('hidden');document.getElementById('preview-title').textContent=name;switchTab('summary');}")

    L("function closePreview(){activeEvalId=null;activeReport=null;currentEvalStructures=[];currentEvalData=null;document.getElementById('preview-panel').classList.add('hidden');}")

    L("function renderReportList(files){console.log('renderReportList called with',files?files.length:'null','files, allReports.length='+allReports.length);var list=document.getElementById('report-list');if(!files||!files.length){list.innerHTML=\"<div class='report-empty'>No PDB reports</div>\";return;}list.innerHTML='';files.forEach(function(f){var dm=f.name.match(/(\\d{4}-\\d{2}-\\d{2})/);var item=document.createElement('div');item.className='report-item';item.innerHTML=\"<div class='rname'>\"+escHtml(f.name)+\"</div><div class='rtitle'>\"+(f.title||'')+\"</div><div class='rdate'>\"+(dm?dm[1]:'')+\"</div>\";item.onclick=(function(n,it){return function(){onReportClick(n,it);};})(f.name,item);list.appendChild(item);});}")

    L("function renderReportListInDiv(files,container){console.log('renderReportListInDiv called with',files?files.length:'null','files');if(!container)return;if(!files||!files.length){container.innerHTML=\"<div class='report-empty' style='padding:10px;font-size:11px;'>No reports</div>\";return;}var html=\"<div style='font-size:11px;color:var(--primary);margin-bottom:8px;'>Reports</div><div style='display:flex;flex-direction:column;gap:4px;'>\";files.forEach(function(f){var dm=f.name.match(/(\\d{4}-\\d{2}-\\d{2})/);var dateStr=dm?dm[1]:'';html+=\"<div class='report-item' style='padding:8px 10px;font-size:11px;cursor:pointer;border-radius:6px;background:var(--bg);border:1px solid var(--border);transition:all 0.15s;'><div style='font-size:10px;color:var(--primary);'>\"+escHtml(f.title||f.name)+\"</div><div style='font-size:9px;color:var(--muted);margin-top:2px;'>\"+dateStr+\"</div></div>\";});html+=\"</div>\";container.innerHTML=html;var items=container.querySelectorAll('.report-item');items.forEach(function(item,idx){item.onclick=function(){items.forEach(function(i){i.classList.remove('active');});item.classList.add('active');var modal=document.getElementById('report-modal');if(modal){var title=document.getElementById('modal-title');var body=document.getElementById('modal-body');if(title)title.textContent=files[idx].name;if(body){body.innerHTML=\"<div class='preview-empty'><div class='preview-empty-icon'>&#8987;</div>Loading...</div>\";fetch('/api/report?name='+encodeURIComponent(files[idx].name)).then(function(res){return res.text();}).then(function(md){body.innerHTML=\"<div class='md-content'>\"+renderMD(md)+\"</div>\";}).catch(function(){body.innerHTML=\"<div class='preview-empty'><div class='preview-empty-icon'>&#9888;</div>Failed</div>\";});}modal.classList.add('show');}else{showFullReport(files[idx].name);}};});}")

    # FIXED renderMD: use [\s\S] instead of . to match any char including newlines
    L("function renderMD(md){var h=md.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');")
    L("h=h.replace(/```([\\s\\S]*?)```/g,'<pre><code>$1</code></pre>');")
    L("h=h.replace(/`([^`]+)`/g,'<code>$1</code>');")
    L("h=h.replace(/^### (.+)$/gm,'<h3>$1</h3>');")
    L("h=h.replace(/^## (.+)$/gm,'<h2>$1</h2>');")
    L("h=h.replace(/^# (.+)$/gm,'<h1>$1</h1>');")
    L("h=h.replace(/^> (.+)$/gm,'<blockquote>$1</blockquote>');")
    L("h=h.replace(/^- (.+)$/gm,'<li>$1</li>');")
    L("h=h.replace(/(<li>[\\s\\S]*?<\\/li>)+/g,'<ul>$&</ul>');")
    L("h=h.replace(/^\\|.*\\|\\s*$/gm,function(row){var cells=row.split('|').slice(1,-1).map(function(c){return'<td>'+c.trim()+'</td>';}).join('');if(cells.match(/^\\s*[-:]+\\s*$/))return'';return'<tr>'+cells+'</tr>';});")
    L("h=h.replace(/(<tr>[\\s\\S]*?<\\/tr>\\s*)+/g,'<table border=\"1\" cellpadding=\"4\" style=\"border-collapse:collapse;width:100%;font-size:12px;margin:8px 0;\">$&</table>');")
    L("h=h.replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>');")
    L("h=h.replace(/\\*(.+?)\\*/g,'<em>$1</em>');")
    L("h=h.replace(/\\n\\n+/g,'</p><p>');")
    L("return '<p>'+h+'</p>'.replace(/<p>\\s*<\\/p>/g,'');}")
    L('var allEvalReports=[];')
    L('async function loadEvalReports(){try{var data=await fetch("/api/evaluation/reports/list").then(function(r){return r.json();});allEvalReports=data;renderEvalReports();}catch(e){allEvalReports=[];renderEvalReports();}}')
    L('function renderEvalReports(){if(!activeEvalId)return;var list=document.getElementById("preview-content");var entryReports=allEvalReports.filter(function(r){return r.uniprot_id===activeEvalId;});if(!entryReports.length){list.innerHTML="<div class=\'preview-empty\'><div class=\'preview-empty-icon\'>&#128196;</div>No evaluation report for this entry</div>";return;}var html="<div style=\'padding:14px;\'><h3 style=\'margin:0 0 10px;font-size:12px;color:var(--primary);border-bottom:1px solid var(--border);padding-bottom:6px;\'>评估报告</h3><div style=\'display:flex;flex-direction:column;gap:6px;\'>";entryReports.forEach(function(r){var isActive=activeEvalMdReport===r.uniprot_id;var dateStr=r.created?r.created.substring(0,10):\'\';html+="<div class=\'report-item\'"+(isActive?" active":"")+" data-uid=\'"+r.uniprot_id+"\' onclick=\'onEvalMdReportClick(this)\' style=\'padding:8px 10px;font-size:11px;cursor:pointer;border-radius:6px;background:var(--bg);border:1px solid var(--border);transition:all 0.15s;\'><div style=\'font-family:var(--mono);color:var(--secondary);font-size:10px;font-weight:600;\'>"+escHtml(dateStr)+"</div><div style=\'font-size:10px;color:var(--text);margin-top:3px;\'>"+escHtml(r.title||\'\')+"</div><div style=\'font-size:9px;color:var(--muted);margin-top:2px;\'>"+r.uniprot_id+"</div></div>";});html+="</div></div>";list.innerHTML=html;}')

    L('function renderEvalReportsInDiv(container){if(!activeEvalId||!container)return;var entryReports=allEvalReports.filter(function(r){return r.uniprot_id===activeEvalId;});if(!entryReports.length){container.innerHTML="<div class=\'report-empty\' style=\'padding:10px;font-size:11px;\'>No evaluation reports</div>";return;}var html="<div style=\'font-size:11px;color:var(--primary);margin-bottom:8px;\'>Evaluation Reports</div><div style=\'display:flex;flex-direction:column;gap:6px;\'>";entryReports.forEach(function(r){var dateStr=r.created?r.created.substring(0,10):\'\';html+="<div class=\'report-item\' data-uid=\'"+r.uniprot_id+"\' onclick=\'onEvalMdReportClick(this)\' style=\'padding:8px 10px;font-size:11px;cursor:pointer;border-radius:6px;background:var(--bg);border:1px solid var(--border);transition:all 0.15s;\'><div style=\'font-family:var(--mono);color:var(--secondary);font-size:10px;font-weight:600;\'>"+escHtml(dateStr)+"</div><div style=\'font-size:10px;color:var(--primary);margin-top:3px;\'>"+escHtml(r.title||\'\')+"</div></div>";});html+="</div>";container.innerHTML=html;}')

    L("function onEvalMdReportClick(el){var uid=el.getAttribute('data-uid');if(!uid)return;activeEvalMdReport=uid;var reportsDiv=document.getElementById('eval-reports-under');if(reportsDiv)renderEvalReportsInDiv(reportsDiv);var modal=document.getElementById('report-modal');var body=document.getElementById('modal-body');var title=document.getElementById('modal-title');title.textContent='Eval Report: '+uid;body.innerHTML=\"<div class=\\\"preview-empty\\\"><div class=\\\"preview-empty-icon\\\">&#8987;</div>Loading...</div>\";modal.classList.add('show');fetch('/api/evaluation/report?uniprot='+encodeURIComponent(uid)).then(function(res){return res.text();}).then(function(md){body.innerHTML=\"<div class=\\\"md-content\\\">\"+renderMD(md)+\"</div>\";}).catch(function(){body.innerHTML=\"<div class=\\\"preview-empty\\\"><div class=\\\"preview-empty-icon\\\">&#9888;</div>Failed to load</div>\";});}")
    L('window.onEvalMdReportClick=onEvalMdReportClick;')



    L("document.getElementById('sel-week').onchange=function(){var wid=this.value;if(wid==='all'){onWeekClick(null,null);}else{var cards=document.querySelectorAll('#week-list .report-item');var card=null;for(var i=0;i<cards.length;i++){if(cards[i].dataset.wid===wid){card=cards[i];break;}}onWeekClick(wid,card);}};")
    L("document.getElementById('sel-method').onchange=function(){activeMethod=this.value;loadEntries();};")
    L("document.getElementById('btn-search').onclick=function(){activeSearch=document.getElementById('inp-search').value.trim();loadEntries();};")
    L("document.getElementById('inp-search').onkeydown=function(e){if(e.key==='Enter'){activeSearch=this.value.trim();loadEntries();}};")
    L("document.getElementById('btn-reset').onclick=function(){activeWeek=null;activeMethod='all';activeSearch='';sortCol='release_date';sortAsc=false;document.getElementById('sel-week').value='all';document.getElementById('sel-method').value='all';document.getElementById('inp-search').value='';document.querySelectorAll('#week-list .report-item').forEach(function(c){c.classList.remove('active');});document.querySelectorAll('#table-head th').forEach(function(t){t.dataset.sorted='false';t.querySelector('.sort-arrow').innerHTML='&#8645;';});var oldReportsDiv=document.getElementById('week-reports');if(oldReportsDiv)oldReportsDiv.remove();document.getElementById('back-button-container').style.display='none';renderReportList([]);allEntries=[];renderTable([]);};")
    L("document.getElementById('btn-back').onclick=function(){activeWeek=null;document.querySelectorAll('#week-list .report-item').forEach(function(c){c.style.display='';c.classList.remove('active');});var oldReportsDiv=document.getElementById('week-reports');if(oldReportsDiv)oldReportsDiv.remove();document.getElementById('back-button-container').style.display='none';document.getElementById('sel-week').value='all';loadEntries();};")
    L("document.getElementById('btn-close').onclick=closePreview;")
    L("document.querySelectorAll('.preview-tab').forEach(function(t){t.onclick=(function(tab){return function(){switchTab(tab);};})(t.getAttribute('data-tab'));});")

    L("var currentMode='weekly';var activeEvalId=null;var activeEvalSearch='';var currentEvalStructures=[];var currentEvalData=null;")
    L("function setMode(mode){currentMode=mode;activeEvalId=null;currentEvalStructures=[];document.getElementById('btn-mode-weekly').classList.toggle('active',mode==='weekly');document.getElementById('btn-mode-eval').classList.toggle('active',mode==='eval');document.getElementById('btn-mode-weekly').style.background=mode==='weekly'?'rgba(6,182,212,0.12)':'var(--card)';document.getElementById('btn-mode-weekly').style.color=mode==='weekly'?'var(--primary)':'var(--muted)';document.getElementById('btn-mode-weekly').style.borderColor=mode==='weekly'?'rgba(6,182,212,0.4)':'var(--border)';document.getElementById('btn-mode-eval').style.background=mode==='eval'?'rgba(139,92,246,0.12)':'var(--card)';document.getElementById('btn-mode-eval').style.color=mode==='eval'?'var(--secondary)':'var(--muted)';document.getElementById('btn-mode-eval').style.borderColor=mode==='eval'?'rgba(139,92,246,0.4)':'var(--border)';document.getElementById('sidebar-weeks-header').style.display=mode==='weekly'?'block':'none';document.getElementById('week-list').style.display=mode==='weekly'?'flex':'none';document.getElementById('eval-sidebar').style.display=mode==='eval'?'flex':'none';document.getElementById('weekly-toolbar').style.display=mode==='eval'?'none':'flex';document.getElementById('weekly-table').style.display='block';var weekReportsDiv=document.getElementById('week-reports');if(weekReportsDiv)weekReportsDiv.style.display='none';var evalReportsDiv=document.getElementById('eval-reports-under');if(evalReportsDiv)evalReportsDiv.style.display='none';document.getElementById('eval-back-container').style.display='none';document.getElementById('back-button-container').style.display='none';var weekRep=document.getElementById('week-reports');if(weekRep)weekRep.remove();if(mode==='weekly'){activeWeek=null;document.getElementById('preview-panel').classList.add('hidden');document.getElementById('table-body').removeAttribute('data-eval-table');document.querySelectorAll('#week-list .report-item').forEach(function(c){c.style.display='';c.classList.remove('active');});document.getElementById('sel-week').value='all';renderTable(sortEntries(allEntries.slice()));}else{document.getElementById('preview-panel').classList.add('hidden');closePreview();renderEvalTable([]);loadEvalList();}}")

    L("function renderEvalMD(md){var h=md.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');")
    L("h=h.replace(/```([\\s\\S]*?)```/g,'<pre><code>$1</code></pre>');")
    L("h=h.replace(/`([^`]+)`/g,'<code>$1</code>');")
    L("h=h.replace(/^### (.+)$/gm,'<h3>$1</h3>');")
    L("h=h.replace(/^## (.+)$/gm,'<h2>$1</h2>');")
    L("h=h.replace(/^# (.+)$/gm,'<h1>$1</h1>');")
    L("h=h.replace(/^> (.+)$/gm,'<blockquote>$1</blockquote>');")
    L("h=h.replace(/^- (.+)$/gm,'<li>$1</li>');")
    L("h=h.replace(/(<li>[\\s\\S]*?<\\/li>)+/g,'<ul>$&</ul>');")
    L("h=h.replace(/^\\|.*\\|\\s*$/gm,function(row){var cells=row.split('|').slice(1,-1).map(function(c){return'<td>'+c.trim()+'</td>';}).join('');if(cells.match(/^\\s*[-:]+\\s*$/))return'';return'<tr>'+cells+'</tr>';});")
    L("h=h.replace(/(<tr>[\\s\\S]*?<\\/tr>\\s*)+/g,'<table border=\"1\" cellpadding=\"4\" style=\"border-collapse:collapse;width:100%;font-size:12px;margin:8px 0;\">$&</table>');")
    L("h=h.replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>');")
    L("h=h.replace(/\\*(.+?)\\*\\*/g,'<em>$1</em>');")
    L("h=h.replace(/\\n\\n+/g,'</p><p>');")
    L("return '<p>'+h+'</p>'.replace(/<p>\\s*<\\/p>/g,'');}")

    L("async function loadEvalList(){console.log('loadEvalList called, search=',activeEvalSearch);var q=encodeURIComponent(activeEvalSearch);var url='/api/evaluations';if(q)url+='?q='+q;try{var evals=await fetch(url).then(function(r){return r.json();});renderEvalList(evals);}catch(e){renderEvalList([]);}}")

    L("function renderEvalList(evals){var list=document.getElementById('eval-list');if(!evals||!evals.length){list.innerHTML=\"<div class='report-empty' style='font-size:11px;'>\"+(activeEvalSearch?'无匹配结果':'暂无评估记录')+\"</div>\";return;}list.innerHTML='';evals.forEach(function(e){var item=document.createElement('div');item.className='report-item'+(activeEvalId===e.uniprot_id?' active':'');item.dataset.uid=e.uniprot_id;var scores=e.scores||{};var bestScore=0;for(var m in scores)if(scores[m].score>bestScore)bestScore=scores[m].score;var scoreColor=bestScore>=7?'var(--success)':bestScore>=5?'var(--accent)':'var(--danger)';item.innerHTML=\"<div class='rname' style='font-size:11px;'><span style='font-family:var(--mono);color:var(--accent);'>\"+e.uniprot_id+\"</span> <span style='font-size:9px;color:\"+scoreColor+\";'>\"+bestScore+\"</span></div><div class='rtitle' style='font-size:10px;'>\"+escHtml(e.protein_name||'')+\"</div><div class='rdate' style='font-size:9px;color:var(--muted);'>\"+e.gene_name+\"</div>\";item.onclick=(function(uid){return function(){onEvalClick(uid);};})(e.uniprot_id);list.appendChild(item);});}")

    L("document.getElementById('btn-modal-close').onclick=function(){document.getElementById('report-modal').classList.remove('show');};")
    L("document.getElementById('report-modal').onclick=function(e){if(e.target===this)document.getElementById('report-modal').classList.remove('show');};")

    L("async function onEvalClick(uniprotId){activeEvalId=uniprotId;var list=document.getElementById('eval-list');var items=list.querySelectorAll('.report-item');var selectedItem=null;items.forEach(function(i){if(i.dataset.uid===uniprotId){i.classList.add('active');i.style.display='';selectedItem=i;}else{i.classList.remove('active');i.style.display='none';}});if(selectedItem&&selectedItem!==list.firstChild){list.insertBefore(selectedItem,list.firstChild);}document.getElementById('eval-back-container').style.display='block';try{var data=await fetch('/api/evaluations/'+encodeURIComponent(uniprotId)).then(function(r){return r.json();});if(data.error){currentEvalData=null;currentEvalStructures=[];renderEvalTable([]);return;}currentEvalData=data;var rawStructures=data.pdb_structures||[];currentEvalStructures=rawStructures.map(function(s,i){s._origIdx=i;return s;});renderEvalTable(currentEvalStructures);activeEvalMdReport=null;await loadEvalReports();var reportsDiv=document.getElementById('eval-reports-under');if(!reportsDiv){reportsDiv=document.createElement('div');reportsDiv.id='eval-reports-under';reportsDiv.className='eval-reports-under';reportsDiv.style.cssText='padding:8px 10px;border-top:1px solid var(--border);background:var(--card);margin-top:4px;';}if(selectedItem){selectedItem.insertAdjacentElement('afterend',reportsDiv);}renderEvalReportsInDiv(reportsDiv);if(reportsDiv)reportsDiv.style.display='block';}catch(e){currentEvalData=null;currentEvalStructures=[];renderEvalTable([]);}}")

    
    
    
    L("function renderEvalTable(structures){var tbody=document.getElementById('table-body');tbody.setAttribute('data-eval-table','true');document.getElementById('entry-count').textContent=structures.length+' PDB structures';if(!structures.length){tbody.innerHTML=\"<tr><td colspan='7'><div class='preview-empty'><div class='preview-empty-icon'>&#128269;</div>No PDB structures</div></td></tr>\";return;}var html=[];for(var i=0;i<structures.length;i++){var s=structures[i];var pdbId=typeof s==='string'?s:(s.pdb_id||'');var method=typeof s==='string'?'':(s.method||'');var res=typeof s==='string'?null:s.resolution;var title=typeof s==='string'?'':(s.title||'');var releaseDate=typeof s==='string'?'':(s.release_date||'');var ligand=typeof s==='string'?'':(s.ligand||s.ligands||'');var journalIf=typeof s==='string'?null:(s.journal_if||s.if||null);var journal=typeof s==='string'?'':(s.journal||'');var bClass='badge-oth',mLabel=method;if(/electron microscopy|cryo/i.test(method)){bClass='badge-em';mLabel='Cryo-EM';}else if(/x-ray/i.test(method)){bClass='badge-xr';mLabel='X-ray';}else if(/nmr/i.test(method)){bClass='badge-nmr';mLabel='NMR';}var rClass='res-mid',rStr='-';if(res!=null&&!isNaN(res)){rClass=res<=2.0?'res-good':res>3.5?'res-poor':'res-mid';rStr=Number(res).toFixed(2);}var ifBadge='';if(journalIf!=null){var tier='low';if(journalIf>=20)tier='top';else if(journalIf>=10)tier='high';else if(journalIf>=5)tier='mid';ifBadge=\"<span class='if-badge tier-\"+tier+\"'>IF \"+Number(journalIf).toFixed(1)+\"</span>\";}var ligs=ligand?(ligand.split(/;/).map(function(l){return l.trim();}).filter(Boolean)):[];var ligHtml='-';if(ligs.length){var chips=[];for(var li=0;li<ligs.length;li++){chips.push(\"<span class='lig-chip' data-lig='\"+escHtml(ligs[li])+\"' data-idx='\"+(s._origIdx!=null?s._origIdx:i)+\"'>\"+escHtml(ligs[li])+\"</span>\");}ligHtml=chips.join('');}var titleShort=title.substring(0,80);html.push(\"<tr><td><span class='pdb-link' data-idx='\"+(s._origIdx!=null?s._origIdx:i)+\"' data-pdb='\"+escHtml(pdbId)+\"' style='font-family:var(--mono);font-weight:700;color:var(--primary);cursor:pointer;font-size:12px;'>\"+escHtml(pdbId)+\"</span></td><td><span class='method-badge \"+bClass+\"'>\"+escHtml(mLabel)+\"</span></td><td><span class='res \"+rClass+\"'>\"+(rStr!=='-'?rStr+' A':'-')+\"</span></td><td>\"+ifBadge+\"</td><td class='title-cell' title='\"+escHtml(title)+\"'>\"+escHtml(titleShort||'-')+\"</td><td>\"+(releaseDate||'-')+\"</td><td class='lig-cell'>\"+ligHtml+\"</td></tr>\");}tbody.innerHTML=html.join('');}")



    L("function showEvalPreview(data){currentEvalData=data;document.getElementById('preview-panel').classList.remove('hidden');document.getElementById('preview-title').textContent=data?data.uniprot_id:'—';showEvalSummary();switchTab('summary');}")
    L("function showEvalSummary(){var data=currentEvalData;var c=document.getElementById('preview-content');if(!data){c.innerHTML=\"<div class='preview-empty'><div class='preview-empty-icon'>&#9888;</div>Failed to load</div>\";return;}var covColor=data.coverage>=50?'var(--success)':'var(--accent)';var uniprot=data.uniprot||{};var scores=data.scores||{};var scoresHtml='';for(var method in scores){var info=scores[method];var pct=info.score*10;var color=info.score>=7?'var(--success)':info.score>=5?'var(--accent)':'var(--danger)';scoresHtml+='<div style=\"margin-bottom:8px;\"><div style=\"display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px;\"><span>'+method+'</span><span style=\"color:'+color+';font-weight:700;\">'+info.score+'/10 '+info.assessment+'</span></div><div style=\"height:3px;background:var(--card);border-radius:2px;\"><div style=\"height:3px;width:'+pct+'%;background:'+color+';border-radius:2px;\"></div></div></div>';}c.innerHTML=\"<div class='report-meta'>\"+'<div class=\"mr\"><span class=\"ml\">UniProt</span><span class=\"mv\"><a href=\"https://www.uniprot.org/uniprot/'+data.uniprot_id+'\" target=\"_blank\" style=\"color:var(--primary);\">'+data.uniprot_id+'</a></span></div>'+'<div class=\"mr\"><span class=\"ml\">蛋白名称</span><span class=\"mv\">'+escHtml(uniprot.protein_name||'N/A')+'</span></div>'+'<div class=\"mr\"><span class=\"ml\">基因名</span><span class=\"mv\">'+escHtml((uniprot.gene_names||[]).join(', '))+'</span></div>'+'<div class=\"mr\"><span class=\"ml\">物种</span><span class=\"mv\">'+escHtml(uniprot.organism||'N/A')+'</span></div>'+'<div class=\"mr\"><span class=\"ml\">序列长度</span><span class=\"mv\">'+(uniprot.sequence_length||0)+' aa</span></div>'+'<div class=\"mr\"><span class=\"ml\">覆盖度</span><span class=\"mv\" style=\"color:'+covColor+';font-weight:700;\">'+(data.coverage||0)+'%</span></div>'+'<div class=\"mr\"><span class=\"ml\">PDB结构</span><span class=\"mv\">'+(data.pdb_structures||[]).length+' 个</span></div>'+'</div>'+'<h3 style=\"margin:10px 0 6px;font-size:12px;color:var(--primary);\">可行性评分</h3><div style=\"padding:6px;background:var(--card);border-radius:6px;margin-bottom:8px;\">'+scoresHtml+'</div>';}")
    L("function showEvalFullReport(){var data=currentEvalData;var c=document.getElementById('preview-content');if(!data){c.innerHTML=\"<div class='preview-empty'><div class='preview-empty-icon'>&#9888;</div>No data</div>\";return;}var reportContent=(typeof data==='string')?data:(data.report||'');if(!reportContent){c.innerHTML=\"<div class='preview-empty'><div class='preview-empty-icon'>&#9888;</div>No full report available</div>\";return;}c.innerHTML=\"<div class='md-content'>\"+renderEvalMD(reportContent)+'</div>';}")

    L("var evalSearchTimer=null;document.getElementById('eval-search').addEventListener('input',function(e){clearTimeout(evalSearchTimer);evalSearchTimer=setTimeout(function(){activeEvalSearch=e.target.value.trim();loadEvalList();},300);});document.getElementById('eval-search').addEventListener('keydown',function(e){if(e.key==='Enter'){clearTimeout(evalSearchTimer);activeEvalSearch=e.target.value.trim();loadEvalList();loadEvalReports();}});")
    L("function sortEvalStructures(arr){var copy=arr.slice();for(var si=0;si<copy.length;si++){if(copy[si]._origIdx==null)copy[si]._origIdx=si;}return copy.sort(function(a,b){var col=sortCol;var av=a[col],bv=b[col];var an=parseFloat(av),bn=parseFloat(bv);var aNum=(av!=null&&String(av).trim()!==''&&!isNaN(an));var bNum=(bv!=null&&String(bv).trim()!==''&&!isNaN(bn));var cmp;if(aNum&&bNum){cmp=an-bn;}else if(aNum){cmp=-1;}else if(bNum){cmp=1;}else{cmp=String(av||'').localeCompare(String(bv||''));}return sortAsc?cmp:-cmp;});}")
    L("document.getElementById('btn-mode-weekly').onclick=function(){setMode('weekly');};")
    L("document.getElementById('btn-mode-eval').onclick=function(){setMode('eval');};")
    L("document.getElementById('btn-eval-back').onclick=function(){activeEvalId=null;document.querySelectorAll('#eval-list .report-item').forEach(function(i){i.style.display='';i.classList.remove('active');});document.getElementById('eval-back-container').style.display='none';var reportsDiv=document.getElementById('eval-reports-under');if(reportsDiv){reportsDiv.remove();}renderEvalTable([]);};")
    L("document.getElementById('btn-modal-close').onclick=function(){document.getElementById('report-modal').classList.remove('show');};")
    L("document.getElementById('report-modal').onclick=function(e){if(e.target===this)document.getElementById('report-modal').classList.remove('show');};")
    L("init().then(function(){setMode('weekly');});")
    L("})();")

    from pathlib import Path
    SCRIPT_DIR = Path("/tmp/pdb_scripts")
    with open(SCRIPT_DIR / "pdb_app.js", 'w', encoding='utf-8') as f:
        f.writelines(lines)


def init_weekly_reports_db():
    """Create weekly_reports and evaluation_reports tables if they don't exist."""
    conn = get_eval_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_id TEXT UNIQUE,
            week_start TEXT,
            week_end TEXT,
            report_type TEXT DEFAULT 'all',
            title TEXT DEFAULT '',
            filename TEXT,
            content TEXT DEFAULT '',
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uniprot_id TEXT UNIQUE,
            title TEXT DEFAULT '',
            filename TEXT,
            content TEXT DEFAULT '',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    logging.info("[init_weekly_reports_db] tables ready")

    # Migration: import existing .md files into DB
    _migrate_weekly_reports()
    _migrate_evaluation_reports()

def _migrate_weekly_reports():
    """Import weekly .md files from summaries/ into weekly_reports DB table.
    Idempotent: skips if weekly_reports table already has rows with content."""
    try:
        if not REPORTS_DIR.exists():
            logging.info("[_migrate_weekly_reports] summaries dir does not exist, skipping")
            return
        conn = get_eval_db()
        # Skip migration if already populated
        count = conn.execute("SELECT COUNT(*) FROM weekly_reports WHERE content IS NOT NULL AND content != ''").fetchone()[0]
        if count > 0:
            conn.close()
            logging.info(f"[_migrate_weekly_reports] {count} reports already in DB, skipping migration")
            return
        migrated = 0
        for f in sorted(REPORTS_DIR.glob("*.md")):
            try:
                content = f.read_text(encoding='utf-8', errors='ignore')
                # Check if already in DB by filename
                existing = conn.execute(
                    "SELECT id FROM weekly_reports WHERE filename = ?", (f.name,)
                ).fetchone()
                if existing:
                    continue
                # Extract week from filename: "X射线晶体学结构周报-2026-04-15.md"
                week_match = re.search(r'(\d{4}-\d{2}-\d{2})', f.name)
                week_id = week_match.group(1) if week_match else f.stem
                # Determine report_type from filename
                fname_lower = f.name.lower()
                if 'cryo' in fname_lower or '冷冻' in fname_lower:
                    rtype = 'cryoem'
                elif 'x' in fname_lower and ('xray' in fname_lower or '射线' in fname_lower or '晶体' in fname_lower):
                    rtype = 'xray'
                else:
                    rtype = 'all'
                # Extract title from first H1
                h1 = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                title = h1.group(1).strip() if h1 else f.stem
                conn.execute("""
                    INSERT OR IGNORE INTO weekly_reports (week_id, title, filename, report_type, content)
                    VALUES (?, ?, ?, ?, ?)
                """, (week_id, title, f.name, rtype, content))
                migrated += 1
            except Exception as ex:
                logging.info(f"[_migrate_weekly_reports] skip {f.name}: {ex}")
        conn.commit()
        conn.close()
        logging.info(f"[_migrate_weekly_reports] migrated {migrated} weekly reports")
    except Exception as e:
        logging.error(f"[_migrate_weekly_reports] error: {e}")

def _migrate_evaluation_reports():
    """Import evaluation .md files from evaluations/ into evaluation_reports DB table.
    Idempotent: skips if evaluation_reports table already has rows with content."""
    try:
        conn = get_eval_db()
        count = conn.execute("SELECT COUNT(*) FROM evaluation_reports WHERE content IS NOT NULL AND content != ''").fetchone()[0]
        if count > 0:
            conn.close()
            logging.info(f"[_migrate_evaluation_reports] {count} reports already in DB, skipping migration")
            return
        migrated = 0
        eval_dir = EVAL_DATA_DIR
        if not eval_dir.exists():
            logging.info("[_migrate_evaluation_reports] evaluations dir does not exist, skipping")
            conn.close()
            return
        for f in sorted(eval_dir.glob("*.md")):
            try:
                # Only process evaluation report files (not .json)
                if not f.suffix == '.md':
                    continue
                content = f.read_text(encoding='utf-8', errors='ignore')
                existing = conn.execute(
                    "SELECT id FROM evaluation_reports WHERE filename = ?", (f.name,)
                ).fetchone()
                if existing:
                    continue
                # Extract uniprot_id from filename: "Q9GZU1_TRPML1_结构可行性评估.md"
                uniprot_match = re.match(r'^([A-Z0-9]+)_', f.stem)
                uniprot_id = uniprot_match.group(1) if uniprot_match else f.stem
                # Extract title from content
                h1 = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                title = h1.group(1).strip() if h1 else f.stem
                conn.execute("""
                    INSERT OR IGNORE INTO evaluation_reports (uniprot_id, title, filename, content)
                    VALUES (?, ?, ?, ?)
                """, (uniprot_id, title, f.name, content))
                migrated += 1
            except Exception as ex:
                logging.info(f"[_migrate_evaluation_reports] skip {f.name}: {ex}")
        conn.commit()
        conn.close()
        logging.info(f"[_migrate_evaluation_reports] migrated {migrated} evaluation reports")
    except Exception as e:
        logging.error(f"[_migrate_evaluation_reports] error: {e}")


# ─── Flask routes ───────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_eval_db():
    """Get a connection to the evaluation database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_eval_db():
    """Create evaluation tables if they don't exist."""
    conn = get_eval_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            uniprot_id TEXT PRIMARY KEY,
            entry_name TEXT,
            protein_name TEXT,
            gene_names TEXT,
            organism TEXT,
            sequence_length INTEGER,
            coverage REAL DEFAULT 0,
            scores TEXT DEFAULT '{}',
            report TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_pdb_structures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uniprot_id TEXT NOT NULL,
            pdb_id TEXT NOT NULL,
            method TEXT DEFAULT '',
            resolution REAL,
            title TEXT DEFAULT '',
            deposition_date TEXT DEFAULT '',
            release_date TEXT DEFAULT '',
            ligand TEXT DEFAULT '',
            ligand_names TEXT DEFAULT '',
            journal TEXT DEFAULT '',
            journal_if REAL,
            doi TEXT DEFAULT '',
            pubmed_id TEXT DEFAULT '',
            organism TEXT DEFAULT '',
            authors TEXT DEFAULT '',
            is_cryoem INTEGER DEFAULT 0,
            is_xray INTEGER DEFAULT 0,
            is_nmr INTEGER DEFAULT 0,
            if_tier TEXT DEFAULT 'unknown',
            updated_at TEXT DEFAULT '',
            FOREIGN KEY (uniprot_id) REFERENCES evaluations(uniprot_id) ON DELETE CASCADE
        )
    """)
    # Unique index on (uniprot_id, pdb_id)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_eval_pdb
        ON evaluation_pdb_structures(uniprot_id, pdb_id)
    """)
    conn.commit()
    conn.close()

    # Migration: if DB is empty but JSON files exist, import them
    try:
        conn = get_eval_db()
        count = conn.execute('SELECT COUNT(*) FROM evaluations').fetchone()[0]
        conn.close()
        if count == 0:
            logging.info('[init_eval_db] DB empty -- migrating from JSON files...')
            import json as _json
            migrated = 0
            for f in sorted(EVAL_DATA_DIR.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    with open(f, encoding='utf-8') as fp:
                        data = _json.load(fp)
                    uid = data.get('uniprot_id')
                    if uid and save_evaluation(data):
                        migrated += 1
                except Exception as ex:
                    logging.info(f'[init_eval_db] skip {f.name}: {ex}')
            logging.info(f'[init_eval_db] migrated {migrated} evaluations from JSON')
    except Exception as e:
        logging.warning(f'[init_eval_db] migration check error (non-fatal): {e}')


@app.route("/api/snapshots")
def api_snapshots():
    conn = get_db()
    rows = conn.execute("SELECT * FROM weekly_snapshots ORDER BY week_start DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/entries")
def api_entries():
    week_id = request.args.get("week", "all")
    method = request.args.get("method", "all")
    search = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 500)), 500)
    conn = get_db()
    params = []
    if week_id != "all":
        snap = conn.execute("SELECT week_start, week_end FROM weekly_snapshots WHERE week_id = ?", (week_id,)).fetchone()
        if snap:
            q = "SELECT * FROM pdb_structures WHERE release_date BETWEEN ? AND ?"
            params = [snap["week_start"], snap["week_end"]]
            logging.info(f"[api_entries] week={week_id} date_range={snap['week_start']} to {snap['week_end']}")
        else:
            q = "SELECT * FROM pdb_structures WHERE week_id = ?"
            params = [week_id]
            logging.info(f"[api_entries] week={week_id} (fallback to week_id column)")
    else:
        q = "SELECT * FROM pdb_structures WHERE 1=1"
        logging.info(f"[api_entries] week=all (no filter)")
    if method == "cryoem":
        q += " AND is_cryoem = 1"
    elif method == "xray":
        q += " AND is_xray = 1"
    if search:
        s = f"%{search}%"
        q += " AND (pdb_id LIKE ? OR title LIKE ? OR journal LIKE ? OR ligand_info LIKE ?)"
        params += [s, s, s, s]
    q += f" ORDER BY release_date DESC LIMIT {limit}"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    logging.info(f"[api_entries] returning {len(rows)} rows for week={week_id}")
    return jsonify([dict(r) for r in rows])

@app.route("/api/reports/list")
def api_reports_list():
    """List all weekly PDB reports from DB, optionally filtered by type."""
    report_type = request.args.get("type", "all").strip()
    try:
        conn = get_eval_db()
        if report_type in ('cryoem', 'xray', 'nmr'):
            rows = conn.execute(
                "SELECT week_id, title, filename, report_type, created_at "
                "FROM weekly_reports WHERE report_type = ? OR report_type = 'all' ORDER BY week_id DESC",
                (report_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT week_id, title, filename, report_type, created_at "
                "FROM weekly_reports ORDER BY week_id DESC"
            ).fetchall()
        conn.close()
        result = []
        for row in rows:
            rd = dict(row)
            result.append({
                "name": rd.get('week_id', rd.get('filename', '')),
                "file": rd.get('filename', ''),
                "title": rd.get('title', ''),
                "type": rd.get('report_type', ''),
                "created": rd.get('created_at', ''),
            })
        logging.info(f"[api_reports_list] returning {len(result)} weekly reports")
        return jsonify(result)
    except Exception as e:
        logging.error(f"[api_reports_list] error: {e}")
        return jsonify([])

@app.route("/api/report")
def api_report():
    """Get a weekly PDB report by name (week_id or filename stem). Reads from DB."""
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    try:
        conn = get_eval_db()
        # Escape LIKE wildcards in name to prevent injection
        safe_name = name.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        row = conn.execute(
            "SELECT content FROM weekly_reports WHERE week_id = ? OR filename LIKE ?",
            (name, f"%{safe_name}%")
        ).fetchone()
        conn.close()
        if row:
            return Response(row['content'], mimetype="text/markdown; charset=utf-8")
        return jsonify({"error": f"Report '{name}' not found"}), 404
    except Exception as e:
        logging.error(f"[api_report] error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/ligand/<code>")
def api_ligand(code):
    import urllib.request, json
    try:
        url = f"https://data.rcsb.org/rest/v1/core/cheminstance/descriptor/{code.upper()}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            name = data.get("rcsb_chem_instance_descriptor", {}).get("name", code)
            return jsonify({"code": code, "name": name})
    except Exception:
        return jsonify({"code": code, "name": code})

@app.route("/pdb_app.js")
def serve_js():
    import time, os
    js_path = SCRIPT_DIR / "pdb_app.js"
    ts = int(js_path.stat().st_mtime)
    resp = send_file(js_path, mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    return resp

@app.route("/")
def index():
    import time
    html_path = SCRIPT_DIR / "pdb_index.html"
    ts = int(html_path.stat().st_mtime)
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
    html = html.replace('/pdb_app.js"></script>', '/pdb_app.js?v=' + str(ts) + '"></script>')
    return Response(html, mimetype='text/html; charset=utf-8')

# ─── Target Evaluation Storage ───────────────────────────────────────────────
EVAL_DATA_DIR = Path("/Users/lijing/Documents/my note/LLM Wiki/wiki/evaluations")

# Journal Impact Factor lookup (sourced from existing data)
JOURNAL_IF_MAP = {
    'Science': 56.9,
    'Protein Cell': 21.1,
    'Nucleic Acids Res.': 19.2,
    'Nat Commun': 17.7,
    'Nature Communications': 17.7,
    'Nat. Commun.': 17.7,
    'Angew.Chem.Int.Ed.Engl.': 16.6,
    'Angew. Chem. Int. Ed. Engl.': 16.6,
    'J.Am.Chem.Soc.': 15.0,
    'J. Am. Chem. Soc.': 15.0,
    'Proc.Natl.Acad.Sci.USA': 11.1,
    'Proc. Natl. Acad. Sci. USA': 11.1,
    'PNAS': 11.1,
    'Embo J.': 8.3,
    'EMBO J.': 8.3,
    'Int.J.Biol.Macromol.': 8.2,
    'Int. J. Biol. Macromol.': 8.2,
    'J.Med.Chem.': 7.3,
    'J. Med. Chem.': 7.3,
    'Br.J.Pharmacol.': 7.3,
    'Br. J. Pharmacol.': 7.3,
    'Commun Biol': 5.1,
    'Communications Biology': 5.1,
    'J.Biol.Chem.': 4.5,
    'J. Biol. Chem.': 4.5,
    'J. Biol Chem': 4.5,
    'Structure': 4.4,
    'Biochem.J.': 3.7,
    'Biochem. J.': 3.7,
    'Biochemistry': 3.1,
    'J.Struct.Biol.': 3.0,
    'J. Struct. Biol.': 3.0,
    'Acta Biochim.Biophys.Sin.': 2.9,
    'Acta Biochim. Biophys. Sin.': 2.9,
    'Beilstein J Org Chem': 2.8,
    'Chembiochem': 2.4,
    'Acta Crystallogr D Struct Biol': 2.3,
    'Acta Crystallogr. D Struct. Biol.': 2.3,
    'Nat. Struct. Mol. Biol.': 18.0,
    'Nature Structural & Molecular Biology': 18.0,
    'Cell': 45.5,
    'Nature': 43.1,
    'Nat. Med.': 30.4,
    'Nature Medicine': 30.4,
    'eLife': 6.4,
    'Mol. Cell': 15.6,
    'Cell Res.': 44.1,
    'Nat. Biotechnol.': 33.2,
    'Nature Biotechnology': 33.2,
    'Science Advances': 11.7,
}

def get_journal_if(journal_name: str) -> float:
    """Lookup journal IF from name/abbreviation."""
    if not journal_name:
        return None
    # Try exact match first
    if journal_name in JOURNAL_IF_MAP:
        return JOURNAL_IF_MAP[journal_name]
    # Try normalized (lowercase, no extra spaces)
    normalized = journal_name.lower().replace('  ', ' ').strip()
    for k, v in JOURNAL_IF_MAP.items():
        if k.lower() == normalized:
            return v
    return None


EVAL_DATA_DIR.mkdir(exist_ok=True)

def _eval_file(uniprot_id: str) -> Path:
    """JSON file path for an evaluation."""
    return EVAL_DATA_DIR / f"{uniprot_id}.json"

def save_evaluation(result: dict) -> bool:
    """Save evaluation result to SQLite DB (primary) and JSON file (backup)."""
    try:
        import json as _json
        uniprot_id = result.get('uniprot_id')
        if not uniprot_id:
            return False

        # --- Extract main fields ---
        uniprot = result.get('uniprot', {}) or {}
        gene_list = uniprot.get('gene_names', []) or result.get('gene_names', []) or []
        gene_names_str = ', '.join(gene_list) if isinstance(gene_list, list) else str(gene_list or '')

        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        scores_json = _json.dumps(result.get('scores', {}), ensure_ascii=False, default=str)

        # --- Write to SQLite ---
        conn = get_eval_db()
        conn.execute("""
            INSERT OR REPLACE INTO evaluations
            (uniprot_id, entry_name, protein_name, gene_names, organism, sequence_length,
             coverage, scores, report, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uniprot_id,
            uniprot.get('entry_name', '') or result.get('entry_name', ''),
            uniprot.get('protein_name', '') or result.get('protein_name', ''),
            gene_names_str,
            uniprot.get('organism', '') or result.get('organism', ''),
            uniprot.get('sequence_length') or result.get('sequence_length') or 0,
            result.get('coverage', 0) or 0,
            scores_json,
            result.get('report', ''),
            result.get('created_at', now),
            now,
        ))

        # Delete old PDB structures within the same transaction
        conn.execute("DELETE FROM evaluation_pdb_structures WHERE uniprot_id = ?", (uniprot_id,))

        pdb_list = result.get('pdb_structures', []) or []
        for item in pdb_list:
            if isinstance(item, str):
                pdb_id = item
                method = ''
                resolution = None
                title = ''
                deposition_date = ''
                release_date = ''
                ligand = ''
                journal_if = None
            else:
                pdb_id = item.get('pdb_id', '')
                method = item.get('method', '')
                resolution = item.get('resolution')
                title = item.get('title', '')
                deposition_date = item.get('deposition_date', '')
                release_date = item.get('release_date', '')
                ligand = item.get('ligand', '') or item.get('ligands', '') or ''
                journal = item.get('journal', '')
                journal_if = item.get('journal_if') or item.get('if')

            method_lower = method.lower()
            is_cryoem = 1 if ('cryo' in method_lower or 'electron microscopy' in method_lower) else 0
            is_xray   = 1 if 'x-ray' in method_lower or 'xray' in method_lower else 0
            is_nmr    = 1 if 'nmr' in method_lower else 0

            if journal_if is not None:
                if journal_if >= 20: if_tier = 'top'
                elif journal_if >= 10: if_tier = 'high'
                elif journal_if >= 5: if_tier = 'mid'
                else: if_tier = 'low'
            else:
                if_tier = 'unknown'

            conn.execute("""
                INSERT INTO evaluation_pdb_structures
                (uniprot_id, pdb_id, method, resolution, title, deposition_date,
                 release_date, ligand, journal, journal_if, is_cryoem, is_xray, is_nmr, if_tier, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uniprot_id, pdb_id, method, resolution, title, deposition_date,
                  release_date, ligand, journal, journal_if, is_cryoem, is_xray, is_nmr, if_tier, now))

        conn.commit()
        conn.close()

        # --- Also write JSON as backup ---
        file_path = _eval_file(uniprot_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            _json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        logging.info(f"[save_evaluation] saved {uniprot_id} ({len(pdb_list)} structures) to DB + JSON")
        return True
    except Exception as e:
        logging.error(f"Failed to save evaluation: {e}")
        return False


def load_evaluation(uniprot_id: str) -> dict:
    """Load a single evaluation by UniProt ID from SQLite; fallback to JSON."""
    try:
        import json as _json

        # Try SQLite first
        conn = get_eval_db()
        row = conn.execute(
            "SELECT * FROM evaluations WHERE uniprot_id = ?", (uniprot_id,)
        ).fetchone()
        conn.close()

        if row:
            rd = dict(row)
            # Reconstruct pdb_structures list from DB
            conn2 = get_eval_db()
            pdb_rows = conn2.execute(
                "SELECT * FROM evaluation_pdb_structures WHERE uniprot_id = ? ORDER BY pdb_id",
                (uniprot_id,)
            ).fetchall()
            conn2.close()

            pdb_structures = []
            for pr in pdb_rows:
                pd = dict(pr)
                pdb_structures.append({
                    'pdb_id': pd['pdb_id'],
                    'method': pd['method'] or '',
                    'resolution': pd['resolution'],
                    'title': pd['title'] or '',
                    'deposition_date': pd['deposition_date'] or '',
                    'release_date': pd['release_date'] or '',
                    'ligand': pd['ligand'] or '',
                    'journal': pd.get('journal') or '',
                    'journal_if': pd['journal_if'],
                })

            gene_list = rd['gene_names'].split(', ') if rd.get('gene_names') else []
            uniprot_block = {
                'uniprot_id': rd['uniprot_id'],
                'entry_name': rd.get('entry_name', ''),
                'protein_name': rd.get('protein_name', ''),
                'gene_names': gene_list,
                'organism': rd.get('organism', ''),
                'sequence_length': rd.get('sequence_length') or 0,
            }
            raw_scores = _json.loads(rd['scores'] or '{}')
            # Normalize score keys: legacy lowercase → title-case
            scores_normalized = {}
            for k, v in raw_scores.items():
                k_lower = k.lower()
                if k_lower in ('cryoem', 'cryo-em', 'cryo em'):
                    scores_normalized['Cryo-EM'] = v
                elif k_lower in ('xray', 'x-ray', 'x ray'):
                    scores_normalized['X-ray'] = v
                elif k_lower == 'nmr':
                    scores_normalized['NMR'] = v
                else:
                    scores_normalized[k] = v

            return {
                'uniprot': uniprot_block,
                'uniprot_id': rd['uniprot_id'],
                'entry_name': rd.get('entry_name', ''),
                'protein_name': rd.get('protein_name', ''),
                'gene_names': gene_list,
                'organism': rd.get('organism', ''),
                'sequence_length': rd.get('sequence_length') or 0,
                'pdb_structures': pdb_structures,
                'blast_results': [],
                'coverage': rd.get('coverage') or 0,
                'scores': scores_normalized,
                'report': rd.get('report') or '',
                'created_at': rd.get('created_at') or '',
            }

        # Fallback to JSON file
        file_path = _eval_file(uniprot_id)
        if file_path.exists():
            with open(file_path, encoding='utf-8') as f:
                data = _json.load(f)
                logging.info(f"[load_evaluation] {uniprot_id} loaded from JSON (fallback)")
                return data

        return None
    except Exception as e:
        logging.error(f"[load_evaluation] error loading {uniprot_id}: {e}")
        # Fallback to JSON
        try:
            import json as _json2
            file_path = _eval_file(uniprot_id)
            if file_path.exists():
                with open(file_path, encoding='utf-8') as f:
                    return _json2.load(f)
        except Exception:
            pass
        return None


def _normalize_scores(raw: dict) -> dict:
    """Normalize legacy lowercase score keys to title-case."""
    if not raw:
        return {}
    normalized = {}
    for k, v in raw.items():
        k_lower = k.lower()
        if k_lower in ('cryoem', 'cryo-em', 'cryo em'):
            normalized['Cryo-EM'] = v
        elif k_lower in ('xray', 'x-ray', 'x ray'):
            normalized['X-ray'] = v
        elif k_lower == 'nmr':
            normalized['NMR'] = v
        else:
            normalized[k] = v
    return normalized

def list_evaluations(search: str = "") -> list:
    """List all saved evaluations from SQLite, with optional search filter."""
    import json as _json
    try:
        conn = get_eval_db()
        if search:
            q = f"%{search}%"
            rows = conn.execute("""
                SELECT e.*, COUNT(p.pdb_id) as pdb_count
                FROM evaluations e
                LEFT JOIN evaluation_pdb_structures p ON e.uniprot_id = p.uniprot_id
                WHERE e.uniprot_id LIKE ? OR e.protein_name LIKE ? OR e.gene_names LIKE ? OR e.organism LIKE ?
                GROUP BY e.uniprot_id
                ORDER BY e.created_at DESC
            """, (q, q, q, q)).fetchall()
        else:
            rows = conn.execute("""
                SELECT e.*, COUNT(p.pdb_id) as pdb_count
                FROM evaluations e
                LEFT JOIN evaluation_pdb_structures p ON e.uniprot_id = p.uniprot_id
                GROUP BY e.uniprot_id
                ORDER BY e.created_at DESC
            """).fetchall()
        conn.close()

        results = []
        for row in rows:
            rd = dict(row)
            gene_str = rd.get('gene_names') or ''
            gene_list = gene_str.split(', ') if gene_str else []
            results.append({
                'uniprot_id': rd['uniprot_id'],
                'protein_name': rd.get('protein_name') or '',
                'gene_name': gene_str,
                'organism': rd.get('organism') or '',
                'pdb_count': rd.get('pdb_count') or 0,
                'coverage': rd.get('coverage') or 0,
                'scores': _normalize_scores(_json.loads(rd.get('scores') or '{}') if rd.get('scores') else {}),
                'created': rd.get('created_at') or '',
            })

        logging.info(f"[list_evaluations] search='{search}' returning {len(results)} results")
        return results
    except Exception as e:
        logging.error(f"[list_evaluations] error: {e}")
        return []


# ─── Target Evaluation API (for AI agent to submit) ───────────────────────
http_session = None

def _get_session():
    global http_session
    if http_session is None:
        import requests
        s = requests.Session()
        s.trust_env = False
        http_session = s
    return http_session

def evaluate_uniprot(uniprot_id: str) -> dict:
    """Evaluate a UniProt ID: fetch UniProt + PDB data, run BLAST if no structures, generate report."""
    session = _get_session()
    result = {
        'uniprot_id': uniprot_id,
        'success': False,
        'error': None,
        'uniprot': None,
        'pdb_structures': [],
        'blast_results': [],
        'coverage': 0,
        'report': None,
        'scores': {},
        'created_at': '',
    }
    from datetime import datetime
    result['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    try:
        url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}?format=json"
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        entry_name = data.get('uniProtkbId', '')
        protein_name = ''
        pd_rec = data.get('proteinDescription', {})
        if pd_rec.get('recommendedName'):
            protein_name = pd_rec['recommendedName'].get('fullName', {}).get('value', '')

        gene_names = []
        for gene in data.get('genes', []):
            if gene.get('geneName'):
                gene_names.append(gene['geneName'].get('value', ''))

        organism = ''
        org_data = data.get('organism', {})
        if org_data:
            organism = org_data.get('scientificName', '')

        sequence_length = 0
        seq_info = data.get('sequence', {})
        if seq_info:
            sequence_length = seq_info.get('length', 0)

        pdb_ids = []
        for ref in data.get('uniProtKBCrossReferences', []):
            if ref.get('database') == 'PDB':
                pdb_ids.append(ref.get('id', ''))
        pdb_ids = list(set(pdb_ids))

        keywords = []
        for kw in data.get('keywords', []):
            kw_obj = kw.get('keyword')
            if isinstance(kw_obj, dict):
                val = kw_obj.get('value')
                if val:
                    keywords.append(val)

        function = ''
        for comment in data.get('comments', []):
            if isinstance(comment, dict) and comment.get('type') == 'function':
                texts = comment.get('texts', [])
                if texts and isinstance(texts[0], dict):
                    function = texts[0].get('value', '') or ''
                break

        result['uniprot'] = {
            'uniprot_id': uniprot_id,
            'entry_name': entry_name,
            'protein_name': protein_name,
            'gene_names': gene_names,
            'organism': organism,
            'function': function,
            'sequence_length': sequence_length,
            'pdb_ids': pdb_ids,
            'keywords': keywords,
            'mass': seq_info.get('molWeight', 0)
        }

        # Fetch PDB structures (up to 50)
        structures = []
        for pdb_id in pdb_ids[:50]:
            try:
                rcsb_url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
                rcsb_resp = session.get(rcsb_url, timeout=15)
                if rcsb_resp.status_code != 200:
                    continue
                rcsb = rcsb_resp.json()

                struct = rcsb.get('struct', {})
                title = struct.get('title', '') if isinstance(struct, dict) else ''

                # Get method from exptl or rcsb_entry_info
                method = ''
                exptl = rcsb.get('exptl', [])
                if exptl and isinstance(exptl, list) and isinstance(exptl[0], dict):
                    method = exptl[0].get('method', '') or ''
                rcsb_info = rcsb.get('rcsb_entry_info', {})
                if not method and isinstance(rcsb_info, dict):
                    method = rcsb_info.get('experimental_method', '') or ''

                # Get resolution using resolution_combined (works for both X-ray and Cryo-EM)
                resolution = None
                if isinstance(rcsb_info, dict):
                    # resolution_combined works for both X-ray and Cryo-EM
                    res_combined = rcsb_info.get('resolution_combined', [None])
                    if res_combined and res_combined[0] is not None:
                        resolution = res_combined[0]
                    # Fallback for X-ray only: try diffrn_resolution_high
                    if not resolution:
                        diffrn = rcsb_info.get('diffrn_resolution_high', {})
                        if isinstance(diffrn, dict):
                            resolution = diffrn.get('value')
                    # Fallback: try reflns
                    if not resolution:
                        refl = rcsb.get('reflns', [])
                        if refl and isinstance(refl[0], dict):
                            resolution = refl[0].get('d_resolution_high')

                # Get dates from rcsb_accession_info and pdbx_database_status
                acc_info = rcsb.get('rcsb_accession_info', {})
                release_date = ''
                if isinstance(acc_info, dict):
                    release_date = acc_info.get('initial_release_date', '') or ''
                    if release_date:
                        release_date = release_date[:10]  # Get YYYY-MM-DD

                deposition_date = ''
                db_status = rcsb.get('pdbx_database_status', {})
                if isinstance(db_status, dict):
                    deposition_date = db_status.get('recvd_initial_deposition_date', '') or ''
                    if deposition_date:
                        deposition_date = deposition_date[:10]

                # Fetch structure-specific ligands from entry (not protein-level cofactors)
                ligand = ''
                try:
                    # Get entry to find non-polymer entity IDs
                    entry_url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
                    entry_resp = session.get(entry_url, timeout=10)
                    if entry_resp.status_code == 200:
                        entry_data = entry_resp.json()
                        container = entry_data.get('rcsb_entry_container_identifiers', {})
                        nonpoly_ids = container.get('non_polymer_entity_ids', [])
                        if nonpoly_ids:
                            # Fetch each nonpolymer entity to get ligand info
                            ligands = []
                            seen = set()
                            for entity_id in nonpoly_ids[:10]:  # Limit to 10
                                try:
                                    np_url = f"https://data.rcsb.org/rest/v1/core/nonpolymer_entity/{pdb_id}/{entity_id}"
                                    np_resp = session.get(np_url, timeout=5)
                                    if np_resp.status_code == 200:
                                        np_data = np_resp.json()
                                        # Get comp_id from pdbx_entity_nonpoly
                                        entity_nonpoly = np_data.get('pdbx_entity_nonpoly', {})
                                        comp_id = entity_nonpoly.get('comp_id', '')
                                        if comp_id and comp_id not in seen and len(comp_id) <= 5:
                                            # Filter out common solvents/water/ions/buffers
                                            if comp_id not in ['HOH', 'DOD', 'SO4', 'CL', 'NA', 'K', 'MG', 'CA', 'ZN', 'FE', 'CU', 'MN', 'CO',
                                                              'GOL', 'PEG', 'EDO', '1PE', '2PE', '3PE', '4PE', 'MLI', 'ACT', 'NH4', 'NO3',
                                                              'EPE', 'HEP', 'MES', 'TRS', 'TRIS', 'MPO', 'PGE', 'PG4', 'DMS', 'DMSO',
                                                              'IPA', 'BU1', 'BU2', 'BU3', 'MPD', 'PG6', '1PG', '2PG', 'XPE']:
                                                seen.add(comp_id)
                                                ligands.append(comp_id)
                                except Exception:
                                    continue
                            if ligands:
                                ligand = '; '.join(ligands[:10])
                except Exception:
                    pass

                # Fetch journal/citation info from RCSB
                journal = ''
                doi = ''
                pubmed_id = ''
                journal_if = None
                try:
                    cit_url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
                    cit_resp = session.get(cit_url, timeout=10)
                    if cit_resp.status_code == 200:
                        cit_data = cit_resp.json()
                        citations = cit_data.get('citation', [])
                        primary = None
                        for c in citations:
                            if c.get('rcsb_is_primary') == 'Y':
                                primary = c
                                break
                        if primary is None and citations:
                            primary = citations[0]
                        if primary:
                            journal = primary.get('journal_abbrev', '') or primary.get('rcsb_journal_abbrev', '')
                            doi = primary.get('pdbx_database_id_DOI', '')
                            pubmed = primary.get('pdbx_database_id_PubMed', '')
                            pubmed_id = str(pubmed) if pubmed else ''
                            # Lookup IF from journal name
                            journal_if = get_journal_if(journal)
                except Exception:
                    pass

                structures.append({
                    'pdb_id': pdb_id,
                    'title': title,
                    'method': method,
                    'resolution': resolution,
                    'deposition_date': deposition_date,
                    'release_date': release_date,
                    'ligand': ligand,
                    'journal': journal,
                    'doi': doi,
                    'pubmed_id': pubmed_id,
                    'journal_if': journal_if
                })
            except Exception:
                continue

        result['pdb_structures'] = structures

        # Calculate coverage
        coverage = 0
        if sequence_length > 0 and structures:
            covered = set()
            for pdb_id in [s['pdb_id'] for s in structures]:
                try:
                    map_url = f"https://www.ebi.ac.uk/pdbe/api/mappings/all_isoforms/{pdb_id.lower()}"
                    map_resp = session.get(map_url, timeout=10)
                    if map_resp.status_code == 200:
                        map_data = map_resp.json()
                        unp_data = map_data.get(pdb_id.lower(), {}).get('UniProt', {})
                        for uid, info in unp_data.items():
                            if uid.upper() != uniprot_id.upper() and not uid.startswith(uniprot_id.upper()):
                                continue
                            for m in info.get('mappings', []):
                                s_pos = m.get('unp_start')
                                e_pos = m.get('unp_end')
                                if s_pos and e_pos:
                                    for p in range(s_pos, e_pos + 1):
                                        covered.add(p)
                except Exception:
                    continue
            coverage = min(len(covered) / sequence_length * 100, 100)
        result['coverage'] = round(coverage, 1)

        # BLAST search if poor coverage
        blast_results = []
        if (coverage < 50 or len(structures) < 5) and sequence_length > 0:
            taxonomy_id = None
            org_data = data.get('organism', {})
            if org_data:
                taxonomy_id = org_data.get('taxonId')

            if taxonomy_id:
                try:
                    search_url = "https://rest.uniprot.org/uniprotkb/search"
                    params = {
                        'query': f'taxon_id:{taxonomy_id}',
                        'format': 'json',
                        'size': 20,
                        'fields': 'accession,gene_names,protein_name,organism_name'
                    }
                    search_resp = session.get(search_url, params=params, timeout=20)
                    if search_resp.status_code == 200:
                        search_data = search_resp.json()
                        for entry in search_data.get('results', []):
                            acc = entry.get('primaryAccession', '')
                            if acc == uniprot_id:
                                continue
                            gene_list = entry.get('genes', [])
                            gene_name = gene_list[0].get('geneName', {}).get('value', '') if gene_list else ''
                            prot_rec = entry.get('proteinName', {})
                            prot_name = prot_rec.get('fullName', {}).get('value', '') if isinstance(prot_rec, dict) else ''
                            org_rec = entry.get('organism', {})
                            org_name = org_rec.get('scientificName', '') if isinstance(org_rec, dict) else ''
                            blast_results.append({
                                'uniprot_id': acc,
                                'gene_name': gene_name,
                                'protein_name': (prot_name or '')[:100],
                                'organism': org_name
                            })
                except Exception:
                    pass

            if len(blast_results) < 10 and taxonomy_id:
                try:
                    pdb_search_url = "https://search.rcsb.org/rcsbsearch/v1/query"
                    pdb_query = {
                        "query": {"type": "group", "logical_operator": "and",
                            "nodes": [{"type": "taxonomy", "operator": "exact_match", "value": str(taxonomy_id)}]},
                        "return_type": "entry",
                        "request_options": {"page_size": 20, "results_content_type": ["experimental"]}
                    }
                    pdb_resp = session.post(pdb_search_url, json=pdb_query, timeout=20)
                    if pdb_resp.status_code == 200:
                        pdb_data = pdb_resp.json()
                        existing = set(r['uniprot_id'].lower() for r in blast_results)
                        for pdb_entry in pdb_data.get('result_set', {}).get('dbrefs', []):
                            pdb_id = pdb_entry.get('uid', '')
                            if pdb_id and pdb_id.lower() not in existing and pdb_id.upper() != uniprot_id.upper():
                                blast_results.append({
                                    'uniprot_id': pdb_id,
                                    'gene_name': '',
                                    'protein_name': f'PDB Structure {pdb_id}',
                                    'organism': result['uniprot']['organism'] or 'Various'
                                })
                                if len(blast_results) >= 20:
                                    break
                except Exception:
                    pass

        result['blast_results'] = blast_results[:20]

        # Scores first (needed for report)
        result['scores'] = _calculate_feasibility_scores(result)

        # Report
        result['report'] = _generate_evaluation_report(result)
        result['success'] = True

    except Exception as e:
        logging.error(f"Evaluation failed for {uniprot_id}: {e}")
        err_msg = str(e)
        err_msg = re.sub(r'\d{3} Client Error:.*?(?=\n|$)', 'API请求失败', err_msg)
        err_msg = re.sub(r'HTTPError.*?(?=\n|$)', '网络请求失败', err_msg)
        if '404' in err_msg or 'Not Found' in err_msg:
            err_msg = f"UniProt ID '{uniprot_id}' 未找到"
        elif '400' in err_msg or 'Bad Request' in err_msg:
            err_msg = f"UniProt ID '{uniprot_id}' 格式无效"
        result['error'] = err_msg

    return result

def _generate_evaluation_report(data: dict) -> str:
    uniprot = data.get('uniprot', {})
    structures = data.get('pdb_structures', [])
    blast = data.get('blast_results', [])
    coverage = data.get('coverage', 0)
    scores = data.get('scores', {})

    lines = []
    lines.append(f"# 蛋白质结构可行性评估报告\n")
    lines.append(f"**UniProt ID**: {uniprot.get('uniprot_id', 'N/A')} | **{uniprot.get('protein_name', 'N/A')}**\n")
    lines.append(f"**基因名**: {', '.join(uniprot.get('gene_names', []) or ['N/A'])} | **物种**: {uniprot.get('organism', 'N/A')}\n")
    lines.append(f"**序列长度**: {uniprot.get('sequence_length', 0)} aa | **分子量**: {(lambda m: f'{m:.0f} Da' if m is not None else 'N/A')(uniprot.get('mass'))}\n")
    lines.append(f"**已有PDB结构**: {len(structures)} 个 | **覆盖度**: {coverage:.1f}%\n")

    if uniprot.get('function'):
        lines.append(f"\n## 功能描述\n{uniprot['function']}\n")

    if scores:
        lines.append("\n## 可行性评分\n")
        lines.append("| 方法 | 评分 | 评估 |\n")
        lines.append("|------|------|------|\n")
        for method, info in scores.items():
            score = info.get('score', 0)
            stars = '★' * max(1, min(5, round(score / 2)))
            lines.append(f"| {method} | {score}/10 {stars} | {info.get('assessment', 'N/A')} |\n")

    if structures:
        lines.append("\n## PDB 结构详情\n")
        cryoem = [s for s in structures if 'electron microscopy' in s.get('method', '').lower() or 'cryo' in s.get('method', '').lower()]
        xray = [s for s in structures if 'x-ray' in s.get('method', '').lower() or 'diffraction' in s.get('method', '').lower()]
        nmr = [s for s in structures if 'nmr' in s.get('method', '').lower()]
        lines.append(f"- Cryo-EM: {len(cryoem)} 个\n")
        lines.append(f"- X-ray: {len(xray)} 个\n")
        lines.append(f"- NMR: {len(nmr)} 个\n")
        lines.append("\n| PDB ID | 方法 | 分辨率 | 标题 |\n")
        lines.append("|--------|------|--------|------|\n")
        for s in structures[:20]:
            method = s.get('method', 'N/A')
            m_label = 'Cryo-EM' if 'cryo' in method.lower() else 'X-ray' if 'x-ray' in method.lower() else method
            res = f"{s['resolution']:.2f} Å" if s.get('resolution') else '-'
            title = (s.get('title') or '')[:60]
            lines.append(f"| {s['pdb_id']} | {m_label} | {res} | {title} |\n")
    else:
        lines.append("\n## PDB 结构详情\n")
        lines.append("*暂无已发表的PDB结构数据*\n")

    if blast:
        lines.append("\n## 同源蛋白 (BLAST搜索)\n")
        lines.append(f"找到 {len(blast)} 个相似蛋白:\n\n")
        lines.append("| UniProt ID | 基因名 | 蛋白质名称 |\n")
        lines.append("|------------|--------|------------|\n")
        for r in blast[:15]:
            lines.append(f"| {r.get('uniprot_id')} | {r.get('gene_name', 'N/A')} | {r.get('protein_name', 'N/A')} |\n")

    lines.append("\n## 实验建议\n")
    if coverage >= 80 and len(structures) >= 3:
        lines.append("✅ **高度可行** - 该蛋白已有良好的结构覆盖，建议基于现有结构开展工作。\n")
        if structures:
            best = min(structures, key=lambda s: s.get('resolution') or 999)
            lines.append(f"最佳结构: {best['pdb_id']} (分辨率: {best.get('resolution', 'N/A')} Å)\n")
    elif coverage >= 50 or len(structures) >= 1:
        lines.append("⚠️ **中等可行** - 有一定结构覆盖，建议补足缺失区域。\n")
        if blast:
            lines.append(f"可通过BLAST找到的 {len(blast)} 个同源结构进行建模指导。\n")
    else:
        lines.append("🔴 **挑战性较高** - 结构覆盖不足，建议: \n")
        lines.append("1. 表达纯化蛋白进行结构解析\n")
        lines.append("2. 使用AlphaFold等工具进行结构预测\n")
        lines.append("3. 优先选择结构保守的域进行表达\n")
        if blast:
            lines.append(f"4. 参考 {len(blast)} 个同源蛋白的结构信息\n")

    return ''.join(lines)

def _calculate_feasibility_scores(data: dict) -> dict:
    uniprot = data.get('uniprot', {})
    structures = data.get('pdb_structures', [])
    coverage = data.get('coverage', 0)
    seq_len = uniprot.get('sequence_length', 0)
    scores = {}

    xr_score = 5
    if seq_len < 500: xr_score += 2
    elif seq_len > 1000: xr_score -= 1
    if coverage >= 50: xr_score += 2
    if any('x-ray' in s.get('method', '').lower() for s in structures): xr_score += 1
    if any(s.get('resolution') and s['resolution'] < 2.5 for s in structures): xr_score += 1
    xr_score = max(1, min(10, xr_score))
    scores['X-ray'] = {'score': xr_score, 'assessment': '推荐' if xr_score >= 7 else '可行' if xr_score >= 5 else '困难'}

    mw = uniprot.get('mass', 0)
    em_score = 5
    if mw > 150000: em_score += 3
    elif mw > 50000: em_score += 1
    elif mw < 50000: em_score -= 2
    if any('electron microscopy' in s.get('method', '').lower() or 'cryo' in s.get('method', '').lower() for s in structures): em_score += 2
    if coverage >= 50: em_score += 1
    em_score = max(1, min(10, em_score))
    scores['Cryo-EM'] = {'score': em_score, 'assessment': '高度推荐' if em_score >= 8 else '推荐' if em_score >= 6 else '困难'}

    nmr_score = 5
    if seq_len < 300: nmr_score += 3
    elif seq_len > 500: nmr_score -= 2
    if any('nmr' in s.get('method', '').lower() for s in structures): nmr_score += 1
    nmr_score = max(1, min(10, nmr_score))
    scores['NMR'] = {'score': nmr_score, 'assessment': '推荐' if nmr_score >= 7 else '可行' if nmr_score >= 5 else '困难'}

    return scores

# ─── Flask routes ───────────────────────────────────────────────────────────

@app.route("/api/evaluate")
def api_evaluate():
    """Run an evaluation and save result. Called by AI agent."""
    uniprot_id = request.args.get("uniprot", "").strip()
    if not uniprot_id:
        return jsonify({"success": False, "error": "UniProt ID required"}), 400
    result = evaluate_uniprot(uniprot_id)
    if result.get('success'):
        save_evaluation(result)
    return jsonify(result)

@app.route("/api/evaluations", methods=["GET"])
def api_evaluations_list():
    """List all saved evaluations, with optional search."""
    search = request.args.get("q", "").strip()
    return jsonify(list_evaluations(search))

@app.route("/api/evaluations/<uniprot_id>", methods=["GET"])
def api_evaluation_get(uniprot_id):
    """Get a single saved evaluation."""
    eval_data = load_evaluation(uniprot_id)
    if eval_data is None:
        return jsonify({"error": "Evaluation not found"}), 404
    return jsonify(eval_data)

@app.route("/api/evaluations", methods=["POST"])
def api_evaluations_save():
    """Save an evaluation result (POST JSON body). Called by AI agent."""
    data = request.get_json()
    if not data or not data.get('uniprot_id'):
        return jsonify({"success": False, "error": "uniprot_id required in body"}), 400
    ok = save_evaluation(data)
    return jsonify({"success": ok})

@app.route("/api/evaluations/<uniprot_id>/structures")
def api_evaluation_structures(uniprot_id):
    """Get PDB structures for an evaluation from SQLite DB."""
    try:
        conn = get_eval_db()
        rows = conn.execute("""
            SELECT pdb_id, method, resolution, title, deposition_date, release_date,
                   ligand, journal_if, doi, pubmed_id, organism, authors, if_tier
            FROM evaluation_pdb_structures
            WHERE uniprot_id = ?
            ORDER BY pdb_id
        """, (uniprot_id,)).fetchall()
        conn.close()

        structures = []
        for row in rows:
            rd = dict(row)
            method = rd.get('method') or ''
            method_lower = method.lower()
            m_label = method
            if 'cryo' in method_lower or 'electron microscopy' in method_lower:
                m_label = 'Cryo-EM'
            elif 'x-ray' in method_lower or 'xray' in method_lower:
                m_label = 'X-ray'
            elif 'nmr' in method_lower:
                m_label = 'NMR'

            structures.append({
                'pdb_id': rd['pdb_id'],
                'method': m_label,
                'resolution': rd.get('resolution'),
                'resolution_high': rd.get('resolution'),
                'title': rd.get('title') or '',
                'deposition_date': rd.get('deposition_date') or '',
                'release_date': rd.get('release_date') or '',
                'ligand': rd.get('ligand') or '',
                'journal_if': rd.get('journal_if'),
                'if_tier': rd.get('if_tier') or 'unknown',
                'doi': rd.get('doi') or '',
                'pubmed_id': rd.get('pubmed_id') or '',
                'organism': rd.get('organism') or '',
                'authors': rd.get('authors') or '',
            })
        return jsonify(structures)
    except Exception as e:
        logging.error(f"[api_evaluation_structures] error: {e}")
        return jsonify([])


@app.route("/api/evaluation/reports/list")
def api_evaluation_reports_list():
    """List all evaluation MD reports from the evaluations folder, linked to UniProt IDs."""
    try:
        conn = get_eval_db()
        rows = conn.execute(
            "SELECT uniprot_id, title, filename, created_at FROM evaluation_reports ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            rd = dict(row)
            result.append({
                "uniprot_id": rd.get('uniprot_id', ''),
                "name": rd.get('filename', ''),
                "title": rd.get('title', ''),
                "filename": rd.get('filename', ''),
                "created": rd.get('created_at', ''),
            })
        return jsonify(result)
    except Exception as e:
        logging.error(f"[api_evaluation_reports_list] error: {e}")
        return jsonify([])


@app.route("/api/evaluation/report")
def api_evaluation_report():
    """Get a specific evaluation MD report by UniProt ID or filename."""
    uniprot = request.args.get("uniprot", "").strip()
    filename = request.args.get("filename", "").strip()
    if not uniprot and not filename:
        return jsonify({"error": "uniprot or filename required"}), 400
    try:
        conn = get_eval_db()
        if uniprot:
            row = conn.execute(
                "SELECT content FROM evaluation_reports WHERE uniprot_id = ?", (uniprot,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT content FROM evaluation_reports WHERE filename = ?", (filename,)
            ).fetchone()
        conn.close()
        if row and row['content']:
            return Response(row['content'], mimetype="text/markdown; charset=utf-8")
        return jsonify({"error": "Evaluation report not found"}), 404
    except Exception as e:
        logging.error(f"[api_evaluation_report] error: {e}")
        return jsonify({"error": str(e)}), 500


# ─── Generate HTML + JS, then start ────────────────────────────────────────
if __name__ == "__main__":
    html = open('/tmp/pdb_scripts/pdb_index.html').read() if (SCRIPT_DIR / "pdb_index.html").exists() else None
    if not html:
        import urllib.request
        print("HTML file missing — please run /tmp/write_js.py first")
        exit(1)
    write_js()
    print(f"JS written: {(SCRIPT_DIR / 'pdb_app.js').stat().st_size} bytes")
    print("Open: http://localhost:5555")
    init_eval_db()  # Initialize evaluation DB tables on startup
    init_weekly_reports_db()  # Initialize weekly reports DB on startup
    app.run(host="0.0.0.0", port=5555, debug=False)
