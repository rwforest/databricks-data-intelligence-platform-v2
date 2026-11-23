(function(){
  const script=document.currentScript;
  const base=new URL(".",script.src);
  const manifestUrl=new URL("addons/manifest.json",base);
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
  let current=null,currentFrame=null,opener=null,contextAddon=null,contextButton=null,book=null,currentContext=null,currentMatches=[];

  const normalize=value=>(value||"").toLowerCase().replace(/&/g," and ").replace(/[^a-z0-9]+/g," ").trim();
  const words=value=>[...new Set(normalize(value).split(" ").filter(word=>word.length>2&&!stop.has(word)))];
  function sameOrigin(value){const url=new URL(value,manifestUrl);return url.origin===location.origin?url:null}
  function excerpt(text,phrases){const clean=(text||"").replace(/\s+/g," ").trim();const lower=clean.toLowerCase();let at=-1;for(const phrase of phrases){at=lower.indexOf(phrase);if(at>=0)break}const start=Math.max(0,(at<0?0:at)-70);return(start?"…":"")+clean.slice(start,start+220)+(start+220<clean.length?"…":"")}

  function rank(context){
    if(!book||!context||!context.name)return [];
    const name=normalize(context.name);const phrases=[name,...(aliases[name]||[])].filter(Boolean);const queryWords=words(phrases.join(" ")+" "+context.section+" "+context.tagline);const matches=[];
    for(const chapter of book.chapters)for(const section of chapter.sections){
      const chapterTitle=normalize(chapter.title),sectionTitle=normalize(section.title),text=normalize(section.text);let score=0;
      for(const phrase of phrases){if(sectionTitle.includes(phrase))score+=70;if(chapterTitle.includes(phrase))score+=50;if(text.includes(phrase))score+=12}
      for(const word of queryWords){if(sectionTitle.includes(word))score+=10;if(chapterTitle.includes(word))score+=7;if(text.includes(word))score+=1}
      if(score>=18)matches.push({score,chapter:chapter.slug,chapterTitle:chapter.title,section:section.id,sectionTitle:section.title||chapter.title,excerpt:excerpt(section.text,phrases)});
    }
    matches.sort((a,b)=>b.score-a.score);
    const seen=new Set();return matches.filter(match=>{const key=match.chapter+"#"+match.section;if(seen.has(key))return false;seen.add(key);return true}).slice(0,3);
  }

  function close(){
    if(!current)return;current.remove();current=null;currentFrame=null;document.body.classList.remove("addon-open");
    const params=new URLSearchParams(location.search);for(const key of ["addon","chapter","section"])params.delete(key);history.replaceState(history.state,"",location.pathname+(params.size?"?"+params.toString():"")+location.hash);if(opener)opener.focus();
  }

  function sendContext(){if(currentFrame&&currentContext)currentFrame.contentWindow.postMessage({type:"databricks-addon-context",context:currentContext,matches:currentMatches},location.origin)}
  function open(addon,button,match){
    close();const entry=sameOrigin(addon.entry);if(!entry)return;const params=new URLSearchParams(location.search);params.set("addon",addon.id);
    if(match){params.set("chapter",match.chapter);params.set("section",match.section);entry.searchParams.set("chapter",match.chapter);entry.searchParams.set("section",match.section)}
    history.replaceState(history.state,"",location.pathname+"?"+params.toString()+location.hash);entry.searchParams.set("embedded","1");entry.searchParams.set("theme",document.body.classList.contains("theme-dark")?"dark":"light");
    const shell=document.createElement("section");shell.className="addon-shell";shell.setAttribute("role","dialog");shell.setAttribute("aria-modal","true");shell.setAttribute("aria-label",addon.title);
    const head=document.createElement("header");const title=document.createElement("strong");title.textContent=match?match.sectionTitle:addon.title;const closeButton=document.createElement("button");closeButton.type="button";closeButton.className="addon-close";closeButton.setAttribute("aria-label","Close "+addon.title);closeButton.textContent="×";closeButton.addEventListener("click",close);
    const frame=document.createElement("iframe");frame.src=entry.href;frame.title=addon.title;frame.loading="eager";frame.addEventListener("load",()=>{frame.contentWindow.addEventListener("keydown",event=>{if(event.key==="Escape")close()});sendContext()});
    head.append(title,closeButton);shell.append(head,frame);document.body.append(shell);current=shell;currentFrame=frame;opener=button;document.body.classList.add("addon-open");closeButton.focus();
  }

  function renderContext(){
    if(!contextAddon||!book||!document.body.classList.contains("detail-open"))return;
    const body=document.getElementById("d-body"),title=document.getElementById("d-title");if(!body||!title)return;
    const context={name:title.textContent.trim(),section:(document.getElementById("d-eyebrow")||{}).textContent||"",tagline:(document.getElementById("d-tagline")||{}).textContent||""};
    if(!context.name)return;const signature=[context.name,context.section,context.tagline].join("|");if(body.dataset.bookContext===signature)return;
    body.dataset.bookContext=signature;currentContext=context;currentMatches=rank(context);body.querySelectorAll(".addon-context-card").forEach(node=>node.remove());
    if(!currentMatches.length){sendContext();return}
    const card=document.createElement("section");card.className="addon-context-card";const heading=document.createElement("h4");heading.textContent="From the book";card.append(heading);
    for(const match of currentMatches){const button=document.createElement("button");button.type="button";button.className="addon-context-link";button.innerHTML="<strong></strong><span></span>";button.querySelector("strong").textContent=match.sectionTitle;button.querySelector("span").textContent=match.chapterTitle;button.addEventListener("click",()=>open(contextAddon,contextButton,match));card.append(button)}
    body.append(card);sendContext();
  }

  function install(manifest){
    if(!manifest||manifest.schemaVersion!==1||!Array.isArray(manifest.addons))return;const slot=document.createElement("div");slot.className="addon-slot";const tools=document.querySelector("header.top .htools");(tools||document.body).append(slot);
    for(const addon of manifest.addons){if(!addon||!/^[-a-z0-9]+$/.test(addon.id||"")||!addon.label||!addon.title||!sameOrigin(addon.entry))continue;const button=document.createElement("button");button.type="button";button.className="hbtn addon-launcher";button.title=addon.title;button.innerHTML=icon+"<span></span>";button.querySelector("span").textContent=addon.label;button.addEventListener("click",()=>open(addon,button));slot.append(button);
      if(addon.contextIndex&&sameOrigin(addon.contextIndex)){contextAddon=addon;contextButton=button;fetch(sameOrigin(addon.contextIndex),{cache:"no-store"}).then(response=>response.json()).then(data=>{book=data;renderContext()}).catch(()=>{})}
      if(new URLSearchParams(location.search).get("addon")===addon.id)open(addon,button);
    }
    if(!slot.childElementCount)slot.remove();
  }

  document.addEventListener("keydown",event=>{if(event.key==="Escape"&&current)close()});
  addEventListener("message",event=>{if(!currentFrame||event.origin!==location.origin||event.source!==currentFrame.contentWindow||!event.data)return;if(event.data.type==="databricks-addon-close")close()});
  let timer;new MutationObserver(()=>{clearTimeout(timer);timer=setTimeout(renderContext,0);if(currentFrame)currentFrame.contentWindow.postMessage({type:"databricks-addon-theme",theme:document.body.classList.contains("theme-dark")?"dark":"light"},location.origin)}).observe(document.body,{attributes:true,attributeFilter:["class"],childList:true,subtree:true});
  fetch(manifestUrl,{cache:"no-store"}).then(response=>response.ok&&/json/i.test(response.headers.get("content-type")||"")?response.json():null).then(install).catch(()=>{});
})();
