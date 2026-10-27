JUMP LAB — OPTION A: MY AI HEROES + CURATED COMMUNITY HEROES

1. Replace GitHub www/index.html with JumpLab_OptionA_Hero_Galleries.html.
2. Add community-heroes.json to the www/ directory.
3. Create the www/community-heroes/ folder. Add instructor-approved PNG or WebP images there.
4. Edit www/community-heroes.json to list the images, e.g.:
   {"heroes": [
     {"title": "Rainbow Fox", "image": "community-heroes/rainbow-fox.png"},
     {"title": "Moon Bunny", "image": "community-heroes/moon-bunny.webp"}
   ]}
5. Commit changes and republish on Posit Connect Cloud.

My AI Heroes: Each browser keeps up to 8 recently applied AI heroes in localStorage when capacity permits. Large images may exceed browser storage. Browser data can be erased and does not sync across computers. For classroom reliability, manually save/approve favorite images in GitHub's community-heroes folder.

Community Heroes: These are static files in GitHub; no database or external hosting required. Selecting a hero never calls OpenAI. New heroes appear only after you manually add and deploy them. Do not include student names or identifying details.

Backend: Keep existing working app.py, OPENAI_API_KEY and gpt-image-2.5-flare configuration. No Bluetooth changes.

