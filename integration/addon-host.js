(function(){
  const script=document.currentScript;
  const base=new URL(".",script.src);
  const manifestUrl=new URL("addons/manifest.json",base);
  const icon='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v17H6.5A2.5 2.5 0 0 0 4 22V5.5Z"/><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v17h4.5A2.5 2.5 0 0 1 20 22V5.5Z"/></svg>';
  let current=null;
  let opener=null;
  let currentFrame=null;

  function sameOriginEntry(value){
    const url=new URL(value,manifestUrl);
    return url.origin===location.origin?url:null;
  }

  function close(){
    if(!current) return;
    current.remove();
    current=null;
    currentFrame=null;
    document.body.classList.remove("addon-open");
    const params=new URLSearchParams(location.search);
    params.delete("addon");
    history.replaceState(history.state,"",location.pathname+(params.size?"?"+params.toString():"")+location.hash);
    if(opener) opener.focus();
  }

  function open(addon,button){
    close();
    const entry=sameOriginEntry(addon.entry);
    if(!entry) return;
    const params=new URLSearchParams(location.search);
    params.set("addon",addon.id);
    history.replaceState(history.state,"",location.pathname+"?"+params.toString()+location.hash);
    entry.searchParams.set("embedded","1");
    entry.searchParams.set("theme",document.body.classList.contains("theme-dark")?"dark":"light");
    for(const key of ["chapter","section"]){const value=params.get(key);if(value) entry.searchParams.set(key,value)}
    const shell=document.createElement("section");
    shell.className="addon-shell";
    shell.setAttribute("role","dialog");
    shell.setAttribute("aria-modal","true");
    shell.setAttribute("aria-label",addon.title);
    const head=document.createElement("header");
    const title=document.createElement("strong");title.textContent=addon.title;
    const closeButton=document.createElement("button");closeButton.type="button";closeButton.className="addon-close";closeButton.setAttribute("aria-label","Close "+addon.title);closeButton.textContent="×";closeButton.addEventListener("click",close);
    const frame=document.createElement("iframe");frame.src=entry.href;frame.title=addon.title;frame.loading="eager";
    frame.addEventListener("load",()=>frame.contentWindow.addEventListener("keydown",event=>{if(event.key==="Escape") close()}));
    head.append(title,closeButton);shell.append(head,frame);document.body.append(shell);
    current=shell;currentFrame=frame;opener=button;document.body.classList.add("addon-open");closeButton.focus();
  }

  function install(manifest){
    if(!manifest||manifest.schemaVersion!==1||!Array.isArray(manifest.addons)) return;
    const slot=document.createElement("div");slot.className="addon-slot";
    const tools=document.querySelector("header.top .htools");
    (tools||document.body).append(slot);
    for(const addon of manifest.addons){
      if(!addon||!/^[-a-z0-9]+$/.test(addon.id||"")||!addon.label||!addon.title||!sameOriginEntry(addon.entry)) continue;
      const button=document.createElement("button");button.type="button";button.className="hbtn addon-launcher";button.title=addon.title;button.innerHTML=icon+"<span></span>";button.querySelector("span").textContent=addon.label;button.addEventListener("click",()=>open(addon,button));slot.append(button);
      if(new URLSearchParams(location.search).get("addon")===addon.id) open(addon,button);
    }
    if(!slot.childElementCount) slot.remove();
  }

  document.addEventListener("keydown",event=>{if(event.key==="Escape"&&current) close()});
  addEventListener("message",event=>{
    if(!currentFrame||event.origin!==location.origin||event.source!==currentFrame.contentWindow||!event.data) return;
    if(event.data.type==="databricks-addon-close"){close();return}
    if(event.data.type!=="databricks-addon-location") return;
    const params=new URLSearchParams(location.search);
    params.set("addon",event.data.addon);
    if(event.data.chapter) params.set("chapter",event.data.chapter); else params.delete("chapter");
    if(event.data.section) params.set("section",event.data.section); else params.delete("section");
    history.replaceState(history.state,"",location.pathname+"?"+params.toString()+location.hash);
  });
  new MutationObserver(()=>{if(currentFrame) currentFrame.contentWindow.postMessage({type:"databricks-addon-theme",theme:document.body.classList.contains("theme-dark")?"dark":"light"},location.origin)}).observe(document.body,{attributes:true,attributeFilter:["class"]});
  fetch(manifestUrl,{cache:"no-store"}).then(response=>response.ok&&/json/i.test(response.headers.get("content-type")||"")?response.json():null).then(install).catch(()=>{});
})();
