import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
const base=process.env.ONEAGENT_BASE_URL || 'http://127.0.0.1:3107';
const dir=path.resolve('artifacts/video-work');mkdirSync(dir,{recursive:true});
const scenes=JSON.parse(readFileSync('scripts/video/scenes.json','utf8'));
const response=await fetch(base+'/api/sessions',{method:'POST',headers:{'content-type':'application/json'}});
if(!response.ok)throw Error('The OneAgent server must be running.');
const {id}=await response.json();
const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,recordVideo:{dir,size:{width:1920,height:1080}}});
const page=await context.newPage();
const errors=[];page.on('pageerror',error=>errors.push(error.message));
const timing=[];
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const frame=s=>page.frameLocator('#app-'+s);
async function click(locator){
 await locator.waitFor({state:'visible'});await locator.scrollIntoViewIfNeeded();
 const box=await locator.boundingBox();if(!box)throw Error('Cannot locate the click target');
 const x=box.x+box.width/2,y=box.y+box.height/2;
 await page.evaluate(({x,y})=>window.director.cursor(x,y,false),{x,y});await sleep(650);
 await page.evaluate(({x,y})=>window.director.cursor(x,y,true),{x,y});await locator.click();await sleep(600);await page.evaluate(()=>window.director.hideCursor());
}
async function waitText(surface,text){await frame(surface).getByText(text,{exact:false}).first().waitFor({state:'visible',timeout:20000});await sleep(500);}
async function send(surface,text){const input=frame(surface).getByRole('textbox',{name:'Message Bob'});await click(input);await input.pressSequentially(text,{delay:45});await sleep(500);await click(frame(surface).getByRole('button',{name:'Send message',exact:true}));}
try{
 await page.goto(`${base}/scripts/video/stage.html?session=${id}`);
 await page.evaluate(()=>document.fonts.ready);
 for(const s of ['phone','dayform','stride','desktop'])await frame(s).getByRole('textbox',{name:'Message Bob'}).waitFor({state:'attached',timeout:30000});
 await sleep(1200);
 // A short magenta leader is removed in the edit, aligning narration to the screen capture.
 await page.evaluate(()=>document.getElementById('sync-mask').style.display='block');await sleep(650);
 await page.evaluate(()=>document.getElementById('sync-mask').style.display='none');
 const start=Date.now();
 for(let i=0;i<scenes.length;i++){
  const scene=scenes[i],began=Date.now();
  await page.evaluate(({scene,i,total})=>window.director.show(scene,i,total),{scene,i,total:scenes.length});
  console.log(`Recording ${i+1}/${scenes.length}: ${scene.id}`);
  const item={...scene,start:(began-start)/1000};timing.push(item);
  await sleep(1300);
  if(scene.id==='brief'){
   await send('phone','Find comfortable work sneakers under $120, US 9');
   await waitText('phone','I’ve saved your brief:');
  } else if(scene.id==='dayform'){
   await send('dayform','Will these be comfortable on my walk?');
   await waitText('dayform','Day One is a good match');
  } else if(scene.id==='stride'){
   await send('stride','How does this compare with the first pair?');
   await waitText('stride','Compared with Day One');
  } else if(scene.id==='checkout'){
   await send('dayform','Order this pair');
   const approve=frame('dayform').getByRole('button',{name:'Approve demo order · $107.80'});await approve.waitFor({state:'visible'});
   await sleep(4500);await click(approve);await waitText('dayform','ORDER CONFIRMED');
  } else if(scene.id==='receipt'){
   await waitText('phone','ORDER CONFIRMED');
   await frame('phone').getByText('ORDER CONFIRMED',{exact:true}).scrollIntoViewIfNeeded();
  } else if(scene.id==='desktop'){
   await click(frame('desktop').getByRole('button',{name:'What do you remember?',exact:true}));
   await waitText('desktop','Your brief is US 9');
  } else if(scene.id==='control'){
   await click(frame('desktop').getByRole('button',{name:'Connections',exact:true}).last());
   await frame('desktop').getByRole('dialog').waitFor({state:'visible'});
   await sleep(2200);
   await click(frame('desktop').getByRole('button',{name:'Revoke STRIDE / STUDIO',exact:true}));
   await frame('desktop').getByRole('button',{name:'Connect STRIDE / STUDIO',exact:true}).waitFor({state:'visible'});
  }
  const remaining=scene.duration*1000-(Date.now()-began);if(remaining>0)await sleep(remaining);
  item.end=(Date.now()-start)/1000;
  if(scene.id==='intro')await page.screenshot({path:path.resolve('public/demo/oneagent-poster.png')});
  if(scene.id==='stride')await page.screenshot({path:path.resolve('artifacts/video-work/comparison-frame.png')});
 }
 const elapsed=(Date.now()-start)/1000;
 await page.evaluate(()=>document.getElementById('sync-mask').style.display='block');await sleep(650);
 const video=page.video();await context.close();const raw=await video.path();
 writeFileSync(path.join(dir,'recording.json'),JSON.stringify({raw,elapsed,timing,errors},null,2));
 if(errors.length)throw Error('Browser errors: '+errors.join('; '));
 console.log('Recording saved: '+raw);
}finally{await browser.close();}
