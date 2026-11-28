(function(){
  const script=document.currentScript;
  const base=new URL(".",script.src);
  const manifestUrl=new URL("addons/manifest.json",base);
  const officialIndexUrl=new URL("resources/links.json",base);
  const icon='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v17H6.5A2.5 2.5 0 0 0 4 22V5.5Z"/><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v17h4.5A2.5 2.5 0 0 1 20 22V5.5Z"/></svg>';
  const aliases={
    "unified governance":["unity catalog","data governance"],"open governance":["unity catalog","data governance"],
    "agentic apps":["agent bricks","agentic ai"],"genie":["ai bi genie","agent bricks"],"ai bi":["databricks sql","ai bi"],
    "apps":["databricks apps","intelligent products"],"ingest":["lakeflow connect","data ingestion"],
    "streaming":["structured streaming","real time intelligence"],"agentic data":["lakehouse","data intelligence"],
    "learned knowledge":["retrieval augmented generation","vector search"],"model serving":["ai runtime","model serving"],
    "cloud services integrations":["security first","production grade databricks apps"]
  };
  const stop=new Set(["about","architecture","business","cloud","data","databricks","details","every","external","platform","services","system","what","with"]);
  let current=null,currentFrame=null,currentAddonId=null,opener=null,contextAddon=null,book=null,officialIndex=null,currentContext=null,currentMatches=[],inertSiblings=[];
  const savedStateKey="databricks-addon-state-v1";

  const normalize=value=>(value||"").toLowerCase().replace(/&/g," and ").replace(/[^a-z0-9]+/g," ").trim();
  const words=value=>[...new Set(normalize(value).split(" ").filter(word=>word.length>2&&!stop.has(word)))];
  function sameOrigin(value){const url=new URL(value,manifestUrl);return url.origin===location.origin?url:null}
  function excerpt(text,phrases){const clean=(text||"").replace(/\s+/g," ").trim();const lower=clean.toLowerCase();let at=-1;for(const phrase of phrases){at=lower.indexOf(phrase);if(at>=0)break}const start=Math.max(0,(at<0?0:at)-70);return(start?"…":"")+clean.slice(start,start+220)+(start+220<clean.length?"…":"")}

  function rank(context){
    if(!book||!context||!context.name)return [];
    const name=normalize(context.name);const phrases=[name,...(aliases[name]||[])].filter(Boolean);const queryWords=words(phrases.join(" ")+" "+context.section+" "+context.tagline);const matches=[];
    for(const chapter of book.chapters)for(const section of chapter.sections){
      if(section.depth===1)continue;
      const chapterTitle=normalize(chapter.title),sectionTitle=normalize(section.title),text=normalize(section.text);let score=0;
      for(const phrase of phrases){if(sectionTitle.includes(phrase))score+=70;if(chapterTitle.includes(phrase))score+=50;if(text.includes(phrase))score+=12}
      for(const word of queryWords){if(sectionTitle.includes(word))score+=10;if(chapterTitle.includes(word))score+=7;if(text.includes(word))score+=1}
      if(score>=18)matches.push({score,chapter:chapter.slug,chapterTitle:chapter.title,section:section.id,sectionTitle:section.title||chapter.title,excerpt:excerpt(section.text,phrases)});
    }
    matches.sort((a,b)=>b.score-a.score);
    const seen=new Set();return matches.filter(match=>{const key=match.chapter+"#"+match.section;if(seen.has(key))return false;seen.add(key);return true}).slice(0,3);
  }

  function officialResources(context){
    if(!officialIndex||!context)return [];
    const names=[context.name,...(aliases[normalize(context.name)]||[])].map(normalize);let record=null;
    for(const [name,value] of Object.entries(officialIndex)){if(names.includes(normalize(name))){record=value;break}}
    if(!record)return [];
    const resources=[];const add=(label,title,value)=>{if(!value)return;let url;try{url=new URL(value,location.origin)}catch{return}const host=url.hostname.replace(/^www\./,"");if(!["databricks.com","docs.databricks.com","youtube.com","youtu.be"].some(domain=>host===domain||host.endsWith("."+domain)))return;resources.push({label,title,url:url.href})};
    if(record.doc)add("Documentation","Official documentation",/^https?:/.test(record.doc)?record.doc:"https://docs.databricks.com/aws/en/"+record.doc.replace(/^\/+/,""));
    add("Product","Official product page",record.site);if(record.videos&&record.videos[0])add("Video",record.videos[0].t,"https://www.youtube.com/watch?v="+encodeURIComponent(record.videos[0].id));
    return resources.slice(0,3);
  }

  function close(){
    if(!current)return;if(current.classList.contains("is-fullscreen"))setFullscreen(false);current.remove();current=null;currentFrame=null;currentAddonId=null;sessionStorage.removeItem(savedStateKey);document.body.classList.remove("addon-open");
    const params=new URLSearchParams(location.search);for(const key of ["addon","chapter","section","bookView"])params.delete(key);history.replaceState(history.state,"",location.pathname+(params.size?"?"+params.toString():"")+location.hash);if(opener)opener.focus();
  }

  function sendContext(){if(currentFrame&&currentContext)currentFrame.contentWindow.postMessage({type:"databricks-addon-context",context:currentContext,matches:currentMatches},location.origin)}
  function setFullscreen(enabled){if(!current)return;current.classList.toggle("is-fullscreen",enabled);if(enabled){current.dataset.previousRole=current.getAttribute("role")||"complementary";current.setAttribute("role","dialog");current.setAttribute("aria-modal","true");inertSiblings=[...document.body.children].filter(node=>node!==current&&!node.inert);for(const node of inertSiblings)node.inert=true}else{current.setAttribute("role",current.dataset.previousRole||"complementary");current.removeAttribute("aria-modal");for(const node of inertSiblings)node.inert=false;inertSiblings=[]}const button=current.querySelector(".addon-fullscreen");if(!button)return;button.setAttribute("aria-pressed",String(enabled));button.setAttribute("aria-label",enabled?"Exit full screen reading mode":"Enter full screen reading mode");button.title=button.getAttribute("aria-label");button.querySelector(".addon-fullscreen-label").textContent=enabled?"Exit full screen":"Full screen";button.querySelector(".addon-fullscreen-icon").textContent=enabled?"⊡":"⛶"}
  function handleEscape(){if(current&&current.classList.contains("is-fullscreen")){setFullscreen(false);return}close()}
  function open(addon,button,match,view="section"){
    close();const entry=sameOrigin(addon.entry);if(!entry)return;const params=new URLSearchParams(location.search);params.set("addon",addon.id);
    if(match){params.set("chapter",match.chapter);entry.searchParams.set("chapter",match.chapter);params.set("bookView",view);entry.searchParams.set("view",view);if(view==="section"){params.set("section",match.section);entry.searchParams.set("section",match.section)}else params.delete("section")}
    history.replaceState(history.state,"",location.pathname+"?"+params.toString()+location.hash);entry.searchParams.set("embedded","1");entry.searchParams.set("theme",document.body.classList.contains("theme-dark")?"dark":"light");
    const shell=document.createElement("aside");shell.className="addon-shell";shell.setAttribute("role","complementary");shell.setAttribute("aria-label",addon.title);
    const head=document.createElement("header");const title=document.createElement("strong");title.textContent="From the book";const fullscreenButton=document.createElement("button");fullscreenButton.type="button";fullscreenButton.className="addon-fullscreen";fullscreenButton.setAttribute("aria-pressed","false");fullscreenButton.setAttribute("aria-label","Enter full screen reading mode");fullscreenButton.title="Enter full screen reading mode";fullscreenButton.innerHTML='<span class="addon-fullscreen-icon" aria-hidden="true">⛶</span><span class="addon-fullscreen-label">Full screen</span>';fullscreenButton.addEventListener("click",()=>setFullscreen(!shell.classList.contains("is-fullscreen")));const closeButton=document.createElement("button");closeButton.type="button";closeButton.className="addon-close";closeButton.setAttribute("aria-label","Close "+addon.title);closeButton.textContent="×";closeButton.addEventListener("click",close);
    const frame=document.createElement("iframe");frame.src=entry.href;frame.title=addon.title;frame.loading="eager";frame.addEventListener("load",sendContext);
    head.append(title,fullscreenButton,closeButton);shell.append(head,frame);document.body.append(shell);current=shell;currentFrame=frame;currentAddonId=addon.id;opener=button;sessionStorage.setItem(savedStateKey,JSON.stringify({addon:addon.id,view:match?view:"matches",chapter:match?match.chapter:"",section:match&&view==="section"?match.section:""}));document.body.classList.add("addon-open");closeButton.focus();
  }

  function renderContext(){
    if(!contextAddon||!book||!document.body.classList.contains("detail-open"))return;
    const body=document.getElementById("d-body"),title=document.getElementById("d-title");if(!body||!title)return;
    const context={name:title.textContent.trim(),section:(document.getElementById("d-eyebrow")||{}).textContent||"",tagline:(document.getElementById("d-tagline")||{}).textContent||""};
    if(!context.name)return;const signature=[context.name,context.section,context.tagline].join("|");if(body.dataset.bookContext===signature)return;
    body.dataset.bookContext=signature;currentContext=context;currentMatches=rank(context);body.querySelectorAll(".addon-context-card").forEach(node=>node.remove());
    if(!currentMatches.length){sendContext();return}
    const card=document.createElement("section");card.className="addon-context-card";const heading=document.createElement("h4");heading.textContent="From the book";card.append(heading);
    for(const [index,match] of currentMatches.entries()){
      if(index===1){const more=document.createElement("p");more.className="addon-context-more";more.textContent="More book matches";card.append(more)}
      const item=document.createElement("article");const headingId="addon-match-"+index+"-"+match.section.replace(/[^a-z0-9_-]/gi,"-");item.className="addon-context-link"+(index?" compact":"");item.setAttribute("aria-labelledby",headingId);item.innerHTML='<h5 id="'+headingId+'"></h5><span></span>'+(index?'':'<p></p>')+'<div class="addon-context-actions"></div>';item.querySelector("h5").textContent=match.sectionTitle;item.querySelector("span").textContent=match.chapterTitle;if(!index)item.querySelector("p").textContent=match.excerpt;
      const actions=item.querySelector(".addon-context-actions");const sectionButton=document.createElement("button");sectionButton.type="button";sectionButton.textContent="Read section";sectionButton.setAttribute("aria-label","Read section: "+match.sectionTitle);sectionButton.addEventListener("click",event=>open(contextAddon,event.currentTarget,match,"section"));const chapterButton=document.createElement("button");chapterButton.type="button";chapterButton.className="secondary";chapterButton.textContent="Open complete chapter";chapterButton.setAttribute("aria-label","Open complete chapter: "+match.chapterTitle);chapterButton.addEventListener("click",event=>open(contextAddon,event.currentTarget,match,"chapter"));actions.append(sectionButton,chapterButton);card.append(item);
    }
    const official=officialResources(context);if(official.length){const section=document.createElement("section");section.className="addon-official";const officialHeading=document.createElement("h5");officialHeading.textContent="Official Databricks resources";section.append(officialHeading);const links=document.createElement("div");for(const resource of official){const link=document.createElement("a");link.href=resource.url;link.target="_blank";link.rel="noopener";link.innerHTML="<span></span><strong></strong><b aria-hidden=\"true\">↗</b>";link.querySelector("span").textContent=resource.label;link.querySelector("strong").textContent=resource.title;links.append(link)}section.append(links);card.append(section)}
    body.prepend(card);sendContext();
  }

  function install(manifest){
    if(!manifest||manifest.schemaVersion!==1||!Array.isArray(manifest.addons))return;const slot=document.createElement("div");slot.className="addon-slot";const tools=document.querySelector("header.top .htools");(tools||document.body).append(slot);
    for(const addon of manifest.addons){if(!addon||!/^[-a-z0-9]+$/.test(addon.id||"")||!addon.label||!addon.title||!sameOrigin(addon.entry))continue;const button=document.createElement("button");button.type="button";button.className="hbtn addon-launcher";button.title=addon.title;button.innerHTML=icon+"<span></span>";button.querySelector("span").textContent=addon.label;button.addEventListener("click",()=>open(addon,button));slot.append(button);
      if(addon.contextIndex&&sameOrigin(addon.contextIndex)){contextAddon=addon;Promise.all([fetch(sameOrigin(addon.contextIndex),{cache:"no-store"}).then(response=>response.json()),fetch(officialIndexUrl,{cache:"no-store"}).then(response=>response.ok?response.json():null).catch(()=>null)]).then(([bookData,officialData])=>{book=bookData;officialIndex=officialData;renderContext()}).catch(()=>{})}
      const locationParams=new URLSearchParams(location.search);let saved={};try{saved=JSON.parse(sessionStorage.getItem(savedStateKey)||"{}")||{}}catch{}const shouldRestore=locationParams.get("addon")===addon.id||saved.addon===addon.id;if(shouldRestore){const chapter=locationParams.get("chapter")||saved.chapter,section=locationParams.get("section")||saved.section,view=locationParams.get("bookView")||saved.view||(section?"section":"chapter");open(addon,button,chapter?{chapter,section}:null,view)}
    }
    if(!slot.childElementCount)slot.remove();
  }

  document.addEventListener("keydown",event=>{if(event.key==="Escape"&&current)handleEscape()});
  addEventListener("message",event=>{if(!currentFrame||event.origin!==location.origin||event.source!==currentFrame.contentWindow||!event.data)return;if(event.data.type==="databricks-addon-close")close();if(event.data.type==="databricks-addon-escape")handleEscape();if(event.data.type==="databricks-addon-state"&&["matches","section","chapter"].includes(event.data.view)){const params=new URLSearchParams(location.search);for(const key of ["chapter","section","bookView"])params.delete(key);if(event.data.view!=="matches"&&event.data.chapter){params.set("chapter",event.data.chapter);params.set("bookView",event.data.view);if(event.data.view==="section"&&event.data.section)params.set("section",event.data.section)}sessionStorage.setItem(savedStateKey,JSON.stringify({addon:currentAddonId,view:event.data.view,chapter:event.data.chapter||"",section:event.data.section||""}));history.replaceState(history.state,"",location.pathname+"?"+params.toString()+location.hash)}});
  let timer;new MutationObserver(()=>{clearTimeout(timer);timer=setTimeout(renderContext,0);if(currentFrame)currentFrame.contentWindow.postMessage({type:"databricks-addon-theme",theme:document.body.classList.contains("theme-dark")?"dark":"light"},location.origin)}).observe(document.body,{attributes:true,attributeFilter:["class"],childList:true,subtree:true});
  fetch(manifestUrl,{cache:"no-store"}).then(response=>response.ok&&/json/i.test(response.headers.get("content-type")||"")?response.json():null).then(install).catch(()=>{});
})();
