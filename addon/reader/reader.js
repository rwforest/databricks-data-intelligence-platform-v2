(function(){
  const content=document.getElementById("content");
  const back=document.getElementById("back");
  const kicker=document.getElementById("reader-kicker");
  const contextLabel=document.getElementById("reader-context");
  const bookLink=document.getElementById("reader-book-link");
  const status=document.getElementById("status");
  let book;
  let currentContext=null;
  let currentMatches=[];
  let lastMatchIndex=0;
  let chapterScrollHandler=null;
  const query=()=>new URLSearchParams(location.search);
  const setTheme=theme=>{document.documentElement.classList.toggle("theme-dark",theme==="dark");document.documentElement.classList.toggle("theme-light",theme==="light")};
  const license=()=>'<div class="reader-license">© The Authors 2026 · <a href="https://creativecommons.org/licenses/by-nc-nd/4.0/" target="_blank" rel="noopener">CC BY-NC-ND 4.0</a></div>';
  const chapterNumber=chapter=>{const match=chapter.title.match(/^(\d+)\.\s*/);return match?"Chapter "+match[1]:"Book chapter"};
  const findSection=(chapterSlug,sectionId)=>{const chapter=book&&book.chapters.find(item=>item.slug===chapterSlug);if(!chapter)return null;const section=chapter.sections.find(item=>item.id===sectionId)||chapter.sections.find(item=>item.depth>1)||chapter.sections[0];return {chapter,section}};
  const introductionMatch=()=>{const chapter=book&&book.chapters.find(item=>item.title.replace(/^\d+\.\s*/,"").trim().toLowerCase()==="introduction"),section=chapter&&chapter.sections.find(item=>item.depth>1);return chapter&&section?{chapter:chapter.slug,chapterTitle:chapter.title,section:section.id,sectionTitle:section.title,excerpt:(section.text||"").slice(0,220)+((section.text||"").length>220?"…":""),fallback:true}:null};
  const setHeader=(primary,secondary)=>{kicker.textContent=primary;contextLabel.textContent=secondary};
  const announce=message=>{status.textContent="";requestAnimationFrame(()=>status.textContent=message)};
  const setLocation=(state,mode)=>{const params=query();for(const key of ["chapter","section","view"])params.delete(key);if(state.view!=="matches"){params.set("chapter",state.chapter);params.set("view",state.view);if(state.section)params.set("section",state.section)}if(mode)history[mode+"State"](state,"",location.pathname+"?"+params.toString());if(query().get("embedded")==="1")parent.postMessage({type:"databricks-addon-state",view:state.view,chapter:state.chapter||"",section:state.section||""},location.origin)};
  const clearChapterNavigation=()=>{if(chapterScrollHandler){removeEventListener("scroll",chapterScrollHandler);removeEventListener("resize",chapterScrollHandler);chapterScrollHandler=null}document.documentElement.classList.remove("chapter-toc-passed")};

  function setupChapterNavigation(selectedSection){
    const topToc=content.querySelector(".chapter-toc"),sideToc=content.querySelector(".chapter-side-toc"),headings=[...content.querySelectorAll(".chapter-view h2[id]")];if(!topToc||!sideToc||!headings.length)return;
    let ticking=false;chapterScrollHandler=()=>{if(ticking)return;ticking=true;requestAnimationFrame(()=>{ticking=false;const sideActive=topToc.getBoundingClientRect().bottom<=82&&matchMedia("(min-width:1200px)").matches;document.documentElement.classList.toggle("chapter-toc-passed",sideActive);topToc.inert=sideActive;sideToc.inert=!sideActive;topToc.setAttribute("aria-hidden",String(sideActive));sideToc.setAttribute("aria-hidden",String(!sideActive));let active=selectedSection||headings[0].id;for(const heading of headings){if(heading.getBoundingClientRect().top<=220)active=heading.id;else break}let sideCurrent=null;for(const link of content.querySelectorAll(".chapter-toc a,.chapter-side-toc a")){const current=link.hash==="#"+active;link.classList.toggle("current",current);if(current){link.setAttribute("aria-current","location");if(link.closest(".chapter-side-toc"))sideCurrent=link}else link.removeAttribute("aria-current")}if(sideActive&&sideCurrent){const top=sideCurrent.offsetTop,bottom=top+sideCurrent.offsetHeight,viewTop=sideToc.scrollTop+34,viewBottom=sideToc.scrollTop+sideToc.clientHeight-18;if(top<viewTop)sideToc.scrollTop=Math.max(0,top-34);else if(bottom>viewBottom)sideToc.scrollTop=bottom-sideToc.clientHeight+18}})};addEventListener("scroll",chapterScrollHandler,{passive:true});addEventListener("resize",chapterScrollHandler,{passive:true});chapterScrollHandler();
  }

  function renderMatches(context,matches,historyMode="replace"){
    clearChapterNavigation();currentContext=context||currentContext||{name:"Book introduction"};currentMatches=matches&&matches.length?matches:[introductionMatch()].filter(Boolean);back.hidden=true;setHeader("Relevant Book Content",book.title);
    document.title="Relevant Book Content";setLocation({bookNav:true,view:"matches",canGoBack:false},historyMode);announce(currentMatches[0]&&currentMatches[0].fallback?"No direct match; showing the book introduction":"Returned to book matches");
    if(!currentMatches.length){content.innerHTML='<section class="empty-state"><h1>Book introduction unavailable</h1><p>The book content could not be loaded.</p></section>';return}
    const head=document.createElement("section");head.className="context-head";head.innerHTML='<h1></h1><p></p>';head.querySelector("h1").textContent=currentContext.name;head.querySelector("p").textContent="Relevant passages from the book";
    if(currentMatches[0].fallback)head.querySelector("p").textContent="No direct match — start with the book introduction";
    const list=document.createElement("div");list.className="matches";
    for(const [index,match] of currentMatches.entries()){const button=document.createElement("button");button.type="button";button.className="match-card";button.innerHTML='<strong></strong><span></span><small></small>';button.querySelector("strong").textContent=match.sectionTitle;button.querySelector("span").textContent=match.chapterTitle;button.querySelector("small").textContent=match.excerpt;button.addEventListener("click",()=>{lastMatchIndex=index;openPassage(match.chapter,match.section,{historyMode:"push",canGoBack:true})});list.append(button)}
    content.replaceChildren(head,list);content.insertAdjacentHTML("beforeend",license());requestAnimationFrame(()=>{const target=list.children[lastMatchIndex];if(historyMode===null&&target)target.focus();else content.focus({preventScroll:true})});
  }

  function openPassage(chapterSlug,sectionId,options={historyMode:"replace",canGoBack:false}){
    clearChapterNavigation();const found=findSection(chapterSlug,sectionId);if(!found)return;
    const {chapter,section}=found;back.hidden=false;setHeader(chapterNumber(chapter),chapter.title.replace(/^\d+\.\s*/,""));document.title=section.title+" | "+chapter.title;
    content.innerHTML='<article class="reading-view"><header class="passage-head"><span class="eyebrow">Section</span><h1></h1><button class="chapter-link" type="button" aria-label="Open complete chapter"><span><strong>Open complete chapter</strong><small>Table of contents and every section</small></span><b aria-hidden="true">→</b></button></header><div class="passage"></div></article>'+license();
    content.querySelector(".passage-head h1").textContent=section.title||chapter.title;content.querySelector(".passage").innerHTML=section.bodyHtml||section.html;content.querySelector(".chapter-link").addEventListener("click",()=>openChapter(chapter.slug,section.id));
    setLocation({bookNav:true,view:"section",chapter:chapter.slug,section:section.id,canGoBack:options.canGoBack},options.historyMode);announce("Section opened: "+section.title);content.scrollIntoView();content.focus({preventScroll:true});
  }

  function openChapter(chapterSlug,selectedSection,options={historyMode:"push",canGoBack:true}){
    clearChapterNavigation();const chapter=book&&book.chapters.find(item=>item.slug===chapterSlug);if(!chapter)return;
    back.hidden=false;setHeader(chapterNumber(chapter),"Complete chapter");document.title=chapter.title;
    const root=chapter.sections.find(section=>section.depth===1);const sections=chapter.sections.filter(section=>section.depth>1);
    content.innerHTML='<article class="reading-view chapter-reading"><header class="chapter-intro"><span class="eyebrow">Complete chapter</span><h1></h1></header><nav class="chapter-toc" aria-label="Chapter sections"><strong>In this chapter</strong><div></div></nav><nav class="chapter-side-toc" aria-label="Chapter sections while reading"><strong>In this chapter</strong><div></div></nav><div class="passage chapter-view"></div></article>'+license();
    content.querySelector(".chapter-intro h1").textContent=chapter.title.replace(/^\d+\.\s*/,"");
    const toc=content.querySelector(".chapter-toc div"),sideToc=content.querySelector(".chapter-side-toc div");
    for(const section of sections.filter(section=>section.depth===2)){for(const container of [toc,sideToc]){const link=document.createElement("a");link.href="#"+section.id;link.textContent=section.title;if(section.id===selectedSection){link.className="current";link.setAttribute("aria-current","location")}container.append(link)}}
    content.querySelector(".passage").innerHTML=(root?root.bodyHtml:"")+sections.map(section=>section.html).join("");
    setLocation({bookNav:true,view:"chapter",chapter:chapter.slug,canGoBack:options.canGoBack},options.historyMode);announce("Complete chapter opened: "+chapter.title);
    requestAnimationFrame(()=>{const target=selectedSection&&document.getElementById(selectedSection);if(target)target.scrollIntoView({block:"start"});else content.scrollIntoView();setupChapterNavigation(selectedSection);content.focus({preventScroll:true})});
  }

  back.addEventListener("click",()=>{const state=history.state;if(state&&state.bookNav&&state.canGoBack)history.back();else renderMatches(currentContext,currentMatches)});
  addEventListener("popstate",event=>{const state=event.state;if(!state||!state.bookNav)return;if(state.view==="matches")renderMatches(currentContext,currentMatches,null);else if(state.view==="section")openPassage(state.chapter,state.section,{historyMode:null,canGoBack:state.canGoBack});else if(state.view==="chapter")openChapter(state.chapter,null,{historyMode:null,canGoBack:state.canGoBack})});
  addEventListener("message",event=>{if(event.origin!==location.origin||!event.data)return;if(event.data.type==="databricks-addon-theme")setTheme(event.data.theme);if(event.data.type==="databricks-addon-context"){currentContext=event.data.context;currentMatches=event.data.matches||[];if(!query().get("chapter"))renderMatches(currentContext,currentMatches)}});
  document.addEventListener("keydown",event=>{if(event.key==="Escape"&&query().get("embedded")==="1"){event.preventDefault();parent.postMessage({type:"databricks-addon-escape"},location.origin)}});
  fetch("book.json",{cache:"no-store"}).then(response=>response.json()).then(data=>{book=data;contextLabel.textContent=book.title||contextLabel.textContent;if(book.sourceUrl){bookLink.href=book.sourceUrl;bookLink.textContent=book.title+" — view or download PDF on Springer ↗";bookLink.hidden=false}else bookLink.hidden=true;const params=query();if(params.get("chapter")){if(params.get("view")==="chapter")openChapter(params.get("chapter"),null,{historyMode:"replace",canGoBack:false});else openPassage(params.get("chapter"),params.get("section"),{historyMode:"replace",canGoBack:false})}else if(currentContext)renderMatches(currentContext,currentMatches);else setLocation({bookNav:true,view:"matches",canGoBack:false},"replace")}).catch(()=>{content.innerHTML='<section class="empty-state"><h1>Book content unavailable</h1></section>'});
  setTheme(query().get("theme"));
})();
