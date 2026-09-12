import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
try {
 const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto((process.env.ONEAGENT_BASE_URL || 'http://127.0.0.1:3107')+'/demo/index.html');
 await page.waitForFunction(()=>{const v=document.querySelector('video');return v&&v.readyState>=1;});
 const metadata=await page.locator('video').evaluate(v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,error:v.error}));
 if(metadata.width!==1920 || metadata.height!==1080 || metadata.duration<125 || metadata.error)throw Error('Video metadata check failed: '+JSON.stringify(metadata));
 await page.locator('video').evaluate(async v=>{v.muted=true;v.currentTime=51;await v.play();});
 await page.waitForFunction(()=>document.querySelector('video').currentTime>52);
 await page.locator('video').evaluate(v=>v.pause());
 await page.screenshot({path:'artifacts/video-work/player-preview.png',fullPage:true});
 if(await page.locator('#chapters button').count()!==9)throw Error('Missing chapters');
 if(errors.length)throw Error('Player errors: '+errors.join('; '));
 writeFileSync('artifacts/video-work/playback-verification.json',JSON.stringify({...metadata,playback:true,chapters:9,errors},null,2));
 console.log('Verified browser playback: '+JSON.stringify(metadata));
}finally {await browser.close();}
