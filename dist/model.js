(function(root){
'use strict';
const DEFAULT_PROGRESS=0;
function safeProgress(value,max=405){const n=Number(value);return value!==null && value!=='' && Number.isInteger(n)&&n>=0&&n<=max?n:DEFAULT_PROGRESS;}
function isLocked(entry,progress){return entry.section!=='chapters'||!entry.chapter||entry.chapter.order>progress;}
function searchable(entry,progress){return isLocked(entry,progress)?[entry.chapter?.volume,entry.chapter?.key,entry.date].filter(Boolean).join(' ').toLowerCase():[entry.description,entry.chapter?.label,entry.chapter?.key,entry.chapter?.volume].join(' ').toLowerCase();}
function compareDates(a,b){return (a.sortDate||'9999').localeCompare(b.sortDate||'9999')||a.id.localeCompare(b.id);}
function localAssetPath(path){if(typeof path!=='string'||!/^assets\/(?:originals|images)\/[a-zA-Z0-9/_\-.]+$/.test(path)||path.includes('..'))throw Error('Asset non locale');return path;}
const api={DEFAULT_PROGRESS,safeProgress,isLocked,searchable,compareDates,localAssetPath};
if(typeof module!=='undefined')module.exports=api;else root.ArchiveModel=api;
})(typeof window!=='undefined'?window:globalThis);
