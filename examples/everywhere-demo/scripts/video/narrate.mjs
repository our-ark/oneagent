import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
const dir=path.resolve('artifacts/video-work');mkdirSync(dir,{recursive:true});
const scenes=JSON.parse(readFileSync('scripts/video/scenes.json','utf8'));
for(const scene of scenes){
 const text=path.join(dir,scene.id+'.txt');writeFileSync(text,scene.narration);
 execFileSync('say',['-v',process.env.VIDEO_VOICE || 'Samantha','-r','165','-f',text,'-o',path.join(dir,scene.id+'.aiff')]);
 console.log('Narration: '+scene.id);
}
