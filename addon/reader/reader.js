(function(){
  const chaptersEl=document.getElementById("chapters");
  const contentEl=document.getElementById("content");
  const searchEl=document.getElementById("search");
  const resultsEl=document.getElementById("results");
  const toggleEl=document.getElementById("nav-toggle");
  const scrimEl=document.getElementById("nav-scrim");
  let book;

  const query=()=>new URLSearchParams(location.search);
  const setTheme=theme=>document.documentElement.classList.toggle("theme-dark",theme==="dark");
  const closeNav=()=>{chaptersEl.classList.remove("open");toggleEl.setAttribute("aria-expanded","false");scrimEl.hidden=true};
  const updateUrl=(chapter,section)=>{const params=query();params.set("chapter",chapter);if(section)params.set("section",section);else params.delete("section");history.pushState({},"",location.pathname+"?"+params.toString()+location.hash);if(params.get("embedded")==="1") parent.postMessage({type:"databricks-addon-location",addon:"book",chapter,section:section||""},location.origin)};
  const chapterBySlug=slug=>book.chapters.find(chapter=>chapter.slug===slug)||book.chapters[0];

  function renderNavigation(active){
    const links=book.chapters.map(chapter=>{
      const button=document.createElement("button");
      button.type="button";
      button.className="chapter-link"+(chapter.slug===active?" active":"");
      button.textContent=chapter.title;
      button.addEventListener("click",()=>openChapter(chapter.slug));
      return button;
    });
    const license=document.createElement("div");license.className="reader-license";license.append("© The Authors 2026 · ");
    const licenseLink=document.createElement("a");licenseLink.href="https://creativecommons.org/licenses/by-nc-nd/4.0/";licenseLink.target="_blank";licenseLink.rel="noopener";licenseLink.textContent="CC BY-NC-ND 4.0";license.append(licenseLink);
    chaptersEl.replaceChildren(...links,license);
  }

  function openChapter(slug,section,push=true){
    const chapter=chapterBySlug(slug);
    document.title=chapter.title+" | Databricks Data Intelligence Platform";
    contentEl.innerHTML=chapter.html;
    renderNavigation(chapter.slug);
    closeResults();
    closeNav();
    if(push) updateUrl(chapter.slug,section);
    requestAnimationFrame(()=>{
      const target=section&&document.getElementById(section);
      if(target) target.scrollIntoView(); else contentEl.scrollIntoView();
      contentEl.focus({preventScroll:true});
    });
  }

  function excerpt(text,term){
    const lower=text.toLowerCase();
    const at=lower.indexOf(term);
    const start=Math.max(0,at-70);
    return (start?"…":"")+text.slice(start,start+180).replace(/\s+/g," ")+(start+180<text.length?"…":"");
  }

  function search(term){
    const normalized=term.trim().toLowerCase();
    if(normalized.length<2){closeResults();return}
    const matches=[];
    for(const chapter of book.chapters){
      for(const section of chapter.sections){
        const haystack=(section.title+" "+section.text).toLowerCase();
        if(haystack.includes(normalized)) matches.push({chapter,section,score:(section.title.toLowerCase().includes(normalized)?2:0)+(chapter.title.toLowerCase().includes(normalized)?1:0)});
      }
    }
    matches.sort((a,b)=>b.score-a.score);
    resultsEl.replaceChildren(...matches.slice(0,40).map(match=>{
      const button=document.createElement("button");
      button.type="button";
      button.className="result";
      const title=document.createElement("strong");title.textContent=match.section.title||match.chapter.title;
      const detail=document.createElement("span");detail.textContent=match.chapter.title+" — "+excerpt(match.section.text,normalized);
      button.append(title,detail);
      button.addEventListener("click",()=>openChapter(match.chapter.slug,match.section.id));
      return button;
    }));
    if(!matches.length){const empty=document.createElement("div");empty.className="empty";empty.textContent="No results found";resultsEl.append(empty)}
    resultsEl.hidden=false;
  }

  function closeResults(){resultsEl.hidden=true;resultsEl.replaceChildren()}

  fetch("book.json",{cache:"no-store"}).then(response=>{
    if(!response.ok) throw new Error("Book data could not be loaded");
    return response.json();
  }).then(data=>{
    book=data;
    const params=query();
    openChapter(params.get("chapter"),params.get("section"),false);
  }).catch(error=>{contentEl.innerHTML='<div class="empty">'+error.message+'</div>'});

  searchEl.addEventListener("input",()=>search(searchEl.value));
  searchEl.addEventListener("keydown",event=>{if(event.key==="Escape"){searchEl.value="";closeResults();searchEl.blur()}});
  document.addEventListener("click",event=>{if(!resultsEl.contains(event.target)&&event.target!==searchEl) closeResults()});
  toggleEl.addEventListener("click",()=>{const open=chaptersEl.classList.toggle("open");toggleEl.setAttribute("aria-expanded",String(open));scrimEl.hidden=!open});
  scrimEl.addEventListener("click",closeNav);
  document.addEventListener("keydown",event=>{if(event.key==="Escape"&&query().get("embedded")==="1") parent.postMessage({type:"databricks-addon-close"},location.origin)});
  addEventListener("popstate",()=>{if(book){const params=query();openChapter(params.get("chapter"),params.get("section"),false)}});
  addEventListener("message",event=>{if(event.origin===location.origin&&event.data&&event.data.type==="databricks-addon-theme") setTheme(event.data.theme)});
  setTheme(query().get("theme"));
})();
