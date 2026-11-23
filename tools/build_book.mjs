import fs from "node:fs";
import path from "node:path";
import { marked } from "marked";

const root=path.resolve(import.meta.dirname,"..");
const sourceDir=path.join(root,"book_content");

const slugify=value=>value.toLowerCase().replace(/\\\./g,".").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"")||"section";
const stripHtml=value=>value.replace(/<[^>]*>/g," ").replace(/&[a-z#0-9]+;/gi," ").replace(/\s+/g," ").trim();
const titleFromMarkdown=(markdown,file)=>{
  const match=markdown.match(/^#\s+(.+)$/m);
  return match?match[1].replace(/\\([.])/g,"$1").trim():path.basename(file,".md").replace(/^\d+-/,"").replaceAll("_"," ");
};

const files=fs.readdirSync(sourceDir).filter(file=>file.endsWith(".md")).sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
const fileToSlug=new Map();
const imageNames=new Set(fs.readdirSync(path.join(sourceDir,"images")));
for(const file of files){
  const markdown=fs.readFileSync(path.join(sourceDir,file),"utf8");
  fileToSlug.set(file,slugify(titleFromMarkdown(markdown,file)));
}

const headingCounts=new Map();
const chapterNumberToSlug=new Map(files.filter(file=>/^\d+-\d+\./.test(file)).map(file=>[Number(file.match(/^\d+-(\d+)\./)[1]),fileToSlug.get(file)]));
let currentChapterSlug="";
const decodedUrl=value=>{
  if(!/^\.\/https?___/.test(value)) return null;
  const raw=value.slice(2).replace(/^https___/,"https://").replace(/^http___/,"http://");
  return raw.replaceAll("_","/").replace(/\.md(?=#|$)/,"").replace(/[.]$/,"");
};

marked.use({
  gfm:true,
  renderer:{
    heading({tokens,depth}){
      const text=this.parser.parseInline(tokens);
      const plain=stripHtml(text);
      const base=slugify(plain);
      const count=headingCounts.get(base)||0;
      headingCounts.set(base,count+1);
      const id=count?base+"-"+(count+1):base;
      return `<h${depth} id="${id}">${text}</h${depth}>\n`;
    },
    image({href,title,text}){
      let source=href;
      if(!/^(?:https?:|data:)/.test(source)){
        const name=path.basename(source).replace(/^-/,"");
        if(imageNames.has(name)) source="./images/"+name;
      }
      const safeTitle=title?` title="${title.replaceAll('"','&quot;')}"`:"";
      return `<img src="${source}" alt="${text.replaceAll('"','&quot;')}"${safeTitle} loading="lazy">`;
    },
    link({href,title,tokens}){
      const label=this.parser.parseInline(tokens);
      const external=decodedUrl(href);
      if(external) return `<a href="${external}" target="_blank" rel="noopener">${label}</a>`;
      const chapterMatch=href.match(/^A\d+_\d+_En_(\d+)_Chapter$/);
      if(chapterMatch){
        const chapter=chapterNumberToSlug.get(Number(chapterMatch[1]))||currentChapterSlug;
        return `<a href="?chapter=${encodeURIComponent(chapter)}">${label}</a>`;
      }
      const clean=href.replace(/^\.\//,"");
      const [file,anchor]=clean.split("#",2);
      const target=fileToSlug.get(file);
      if(target) return `<a href="?chapter=${encodeURIComponent(target)}${anchor?`&section=${encodeURIComponent(slugify(anchor))}`:""}">${label}</a>`;
      const safeTitle=title?` title="${title.replaceAll('"','&quot;')}"`:"";
      return `<a href="${href}"${safeTitle}>${label}</a>`;
    }
  }
});

export function buildBook(targetDir=path.join(root,"dist","book")){
const outputDir=path.resolve(targetDir);
const chapters=files.map(file=>{
  const markdown=fs.readFileSync(path.join(sourceDir,file),"utf8");
  headingCounts.clear();
  currentChapterSlug=fileToSlug.get(file);
  const html=marked.parse(markdown);
  const title=titleFromMarkdown(markdown,file);
  const sections=[];
  const headingPattern=/<h([1-6]) id="([^"]+)">([\s\S]*?)<\/h\1>/g;
  const headings=[...html.matchAll(headingPattern)];
  for(let index=0;index<headings.length;index++){
    const start=headings[index].index;
    const bodyStart=start+headings[index][0].length;
    const end=index+1<headings.length?headings[index+1].index:html.length;
    sections.push({id:headings[index][2],title:stripHtml(headings[index][3]),text:stripHtml(html.slice(bodyStart,end)),html:html.slice(start,end)});
  }
  if(!sections.length) sections.push({id:"",title,text:stripHtml(html),html});
  return {slug:fileToSlug.get(file),title,sections};
});

fs.rmSync(outputDir,{recursive:true,force:true});
fs.mkdirSync(outputDir,{recursive:true});
for(const file of ["index.html","reader.css","reader.js"]) fs.copyFileSync(path.join(root,"addon","reader",file),path.join(outputDir,file));
fs.cpSync(path.join(sourceDir,"images"),path.join(outputDir,"images"),{recursive:true});
fs.writeFileSync(path.join(outputDir,"book.json"),JSON.stringify({schemaVersion:1,title:"Databricks Data Intelligence Platform: Powering the Agentic Era",chapters}));
console.log(`Built ${chapters.length} chapters in ${outputDir}`);
return {outputDir,chapters};
}

if(path.resolve(process.argv[1]||"")===path.resolve(import.meta.filename)) buildBook(process.argv[2]);
