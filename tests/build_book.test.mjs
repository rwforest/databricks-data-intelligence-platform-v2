import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { buildBook } from "../tools/build_book.mjs";

const root=path.resolve(import.meta.dirname,"..");

test("book build contains every chapter and resolves local images",()=>{
  const output=fs.mkdtempSync(path.join(os.tmpdir(),"book-addon-"));
  buildBook(output);
  const book=JSON.parse(fs.readFileSync(path.join(output,"book.json"),"utf8"));
  assert.equal(book.schemaVersion,1);
  assert.equal(book.title,"Databricks Data Intelligence Platform: Powering the Agentic Era");
  assert.equal(book.sourceUrl,"https://link.springer.com/book/10.1007/979-8-8688-2524-8");
  assert.equal(book.chapters.length,32);
  assert.ok(book.chapters.some(chapter=>chapter.sections.some(section=>section.depth>1)));
  const sectionHtml=book.chapters.flatMap(chapter=>chapter.sections.map(section=>section.html));
  const imageRefs=sectionHtml.flatMap(html=>[...html.matchAll(/<img src="([^"]+)"/g)].map(match=>match[1]));
  assert.ok(imageRefs.length>250);
  for(const reference of imageRefs){
    if(/^https?:/.test(reference)) continue;
    assert.ok(fs.existsSync(path.resolve(output,reference)),reference);
  }
  const unresolved=sectionHtml.flatMap(html=>[...html.matchAll(/href="([^"]+)"/g)].map(match=>match[1])).filter(reference=>!reference.startsWith("?")&&!reference.startsWith("#")&&!/^(https?:|mailto:)/.test(reference));
  assert.deepEqual(unresolved,[]);
  assert.ok(sectionHtml.every(html=>!/<script\b|\son\w+=|javascript:/i.test(html)));
});
