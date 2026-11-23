(function(){
  const content=document.getElementById("content");
  const back=document.getElementById("back");
  let book;
  let currentContext=null;
  let currentMatches=[];
  const query=()=>new URLSearchParams(location.search);
  const setTheme=theme=>document.documentElement.classList.toggle("theme-dark",theme==="dark");
  const license=()=>'<div class="reader-license">© The Authors 2026 · <a href="https://creativecommons.org/licenses/by-nc-nd/4.0/" target="_blank" rel="noopener">CC BY-NC-ND 4.0</a></div>';
  const findSection=(chapterSlug,sectionId)=>{const chapter=book&&book.chapters.find(item=>item.slug===chapterSlug);if(!chapter)return null;const section=chapter.sections.find(item=>item.id===sectionId)||chapter.sections[0];return {chapter,section}};

  function renderMatches(context,matches){
    currentContext=context;currentMatches=matches||[];back.hidden=true;
    if(!currentMatches.length){content.innerHTML='<section class="empty-state"><h1>No direct book match</h1><p>The selected architecture component is not covered directly in this edition.</p></section>';return}
    const head=document.createElement("section");head.className="context-head";head.innerHTML='<h1></h1><p></p>';head.querySelector("h1").textContent=context.name;head.querySelector("p").textContent="Relevant passages from the book";
    const list=document.createElement("div");list.className="matches";
    for(const match of currentMatches){const button=document.createElement("button");button.type="button";button.className="match-card";button.innerHTML='<strong></strong><span></span><small></small>';button.querySelector("strong").textContent=match.chapterTitle;button.querySelector("span").textContent=match.sectionTitle;button.querySelector("small").textContent=match.excerpt;button.addEventListener("click",()=>openPassage(match.chapter,match.section));list.append(button)}
    content.replaceChildren(head,list);content.insertAdjacentHTML("beforeend",license());content.focus({preventScroll:true});
  }

  function openPassage(chapterSlug,sectionId){
    const found=findSection(chapterSlug,sectionId);if(!found)return;
    const {chapter,section}=found;back.hidden=!currentMatches.length;
    content.innerHTML='<header class="passage-head"><h1></h1><p></p></header><article class="passage"></article>'+license();content.querySelector(".passage-head h1").textContent=section.title||chapter.title;content.querySelector(".passage-head p").textContent=chapter.title;content.querySelector(".passage").innerHTML=section.html;
    const params=query();params.set("chapter",chapter.slug);params.set("section",section.id);history.replaceState({},"",location.pathname+"?"+params.toString());content.scrollIntoView();content.focus({preventScroll:true});
  }

  back.addEventListener("click",()=>renderMatches(currentContext,currentMatches));
  addEventListener("message",event=>{if(event.origin!==location.origin||!event.data)return;if(event.data.type==="databricks-addon-theme")setTheme(event.data.theme);if(event.data.type==="databricks-addon-context")renderMatches(event.data.context,event.data.matches)});
  document.addEventListener("keydown",event=>{if(event.key==="Escape"&&query().get("embedded")==="1")parent.postMessage({type:"databricks-addon-close"},location.origin)});
  fetch("book.json",{cache:"no-store"}).then(response=>response.json()).then(data=>{book=data;const params=query();if(params.get("chapter"))openPassage(params.get("chapter"),params.get("section"))}).catch(()=>{content.innerHTML='<section class="empty-state"><h1>Book content unavailable</h1></section>'});
  setTheme(query().get("theme"));
})();
