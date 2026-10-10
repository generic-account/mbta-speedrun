'use strict';
(() => {
  const data = window.MBTA_DATA;
  const $ = id => document.getElementById(id);
  const svg = $('map'), frame = $('map-frame');
  const NS = 'http://www.w3.org/2000/svg';
  const stations = new Map(data.stations.map(s => [s.id, s]));
  const photos = new Map(data.photos.map(p => [p.file, p]));
  const colors = {Red:'#f05555', Orange:'#f6a341', Blue:'#579cf5', Mattapan:'#e97979'};
  const color = id => colors[id] || '#39b66c';
  const routeNames = new Map(data.routes.map(r => [r.id, r.name]));
  const termini = new Set(['place-alfcl','place-brntn','place-asmnl','place-matt','place-forhl','place-ogmnl','place-lake','place-clmnl','place-river','place-hsmnl','place-mdftf','place-unsqu','place-wondl','place-bomnl']);
  const interchanges = new Set(['place-pktrm','place-gover','place-dwnxg','place-state','place-north','place-kencl','place-coecl','place-lech','place-jfk']);
  let currentStation = null, currentPhotos = [], photoIndex = 0;
  let camera, homeCamera, modalPhotos = [], modalIndex = 0, modalTitle = '';
  const markers = new Map();
  const markerLayer = element('g');
  svg.append(element('image', {href:data.map.image, width:data.map.width, height:data.map.height, 'aria-hidden':'true'}), markerLayer);
  function element(tag, attrs = {}, text) {
    const el = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
    if (text !== undefined) el.textContent = text;
    return el;
  }
  for (const station of stations.values()) {
    const major = termini.has(station.id) || interchanges.has(station.id);
    const group = element('g', {class:'station-marker' + (major ? ' major' : ''), transform:`translate(${station.x} ${station.y})`, tabindex:'0', role:'button', 'aria-label':station.name, 'data-station':station.id});
    group.append(element('title', {}, station.name));
    group.append(element('circle', {r:24, class:'hit-area'}));
    group.append(element('circle', {r:20, class:'selection-ring'}));
    const rim = station.routes.length > 1 && station.routes.some(r=>!r.startsWith('Green')) ? '#ddd' : color(station.routes[0]);
    group.append(element('circle', {r:station.radius*.55, fill:station.photos.length?'#141414':'#fff', stroke:rim, class:'station-dot'}));
    group.addEventListener('click', () => {if (!dragMoved) {selectStation(station.id);showPeek();}});
    group.addEventListener('keydown', event => {
      if (event.key==='Enter'||event.key===' ') {event.preventDefault(); selectStation(station.id);showPeek();}
    });
    group.addEventListener('pointerenter', event => tooltip(station,event));
    group.addEventListener('pointerleave', () => $('map-tooltip').hidden=true);
    markers.set(station.id,group);markerLayer.append(group);
  }
  function tooltip(station,event) {
    if (pointers.size) return;
    const tip=$('map-tooltip'), rect=frame.getBoundingClientRect();
    tip.textContent=station.name;tip.hidden=false;
    tip.style.left=Math.max(8,Math.min(rect.width-225,event.clientX-rect.left+12))+'px';
    tip.style.top=Math.max(50,event.clientY-rect.top-35)+'px';
  }
  function fit() {
    const minX=0,maxX=data.map.width,minY=0,maxY=data.map.height;
    const rect=svg.getBoundingClientRect(),ratio=rect.width/rect.height;
    let width=maxX-minX,height=maxY-minY;
    if(width/height<ratio)width=height*ratio;else height=width/ratio;
    camera={x:(minX+maxX-width)/2,y:(minY+maxY-height)/2,w:width,h:height};
    homeCamera={...camera};renderCamera();
  }
  function renderCamera() {
    svg.setAttribute('viewBox',`${camera.x} ${camera.y} ${camera.w} ${camera.h}`);
    $('zoom-out').disabled=camera.w>=homeCamera.w*1.9;
    $('zoom-in').disabled=camera.w<=homeCamera.w/6;
  }
  function zoom(factor,center={x:camera.x+camera.w/2,y:camera.y+camera.h/2}) {
    const newWidth=Math.min(homeCamera.w*2,Math.max(homeCamera.w/6,camera.w/factor));
    const scale=newWidth/camera.w;
    camera={x:center.x+(camera.x-center.x)*scale,y:center.y+(camera.y-center.y)*scale,w:newWidth,h:camera.h*scale};renderCamera();
  }
  function point(clientX,clientY) {return new DOMPoint(clientX,clientY).matrixTransform(svg.getScreenCTM().inverse());}
  $('zoom-in').onclick=()=>zoom(1.4);$('zoom-out').onclick=()=>zoom(1/1.4);$('reset-map').onclick=fit;
  // One-pointer drag and two-pointer pinch. Browser zoom/scroll remain available outside the map.
  const pointers=new Map();let gesture=null,dragMoved=false;
  function startGesture() {
    const values=[...pointers.values()];
    const middle=values.length>1?{x:(values[0].x+values[1].x)/2,y:(values[0].y+values[1].y)/2}:values[0];
    gesture={camera:{...camera},middle,world:point(middle.x,middle.y),distance:values.length>1?Math.hypot(values[0].x-values[1].x,values[0].y-values[1].y):0};
  }
  svg.addEventListener('pointerdown',event=>{if(event.button!==0)return;dragMoved=false;pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});startGesture();svg.classList.add('dragging');$('map-tooltip').hidden=true;});
  svg.addEventListener('pointermove',event=>{
    if(!pointers.has(event.pointerId))return;
    pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});const values=[...pointers.values()];
    const middle=values.length>1?{x:(values[0].x+values[1].x)/2,y:(values[0].y+values[1].y)/2}:values[0];
    const moved=Math.hypot(middle.x-gesture.middle.x,middle.y-gesture.middle.y);
    if(moved>5 || values.length>1){dragMoved=true;svg.setPointerCapture(event.pointerId);}
    if(!dragMoved)return;
    const scale=values.length>1 && gesture.distance?gesture.distance/Math.max(1,Math.hypot(values[0].x-values[1].x,values[0].y-values[1].y)):1;
    const newWidth=Math.min(homeCamera.w*2,Math.max(homeCamera.w/6,gesture.camera.w*scale));
    const ratio=newWidth/gesture.camera.w;const rect=svg.getBoundingClientRect();
    camera={x:gesture.world.x-(middle.x-rect.left)/rect.width*newWidth,y:gesture.world.y-(middle.y-rect.top)/rect.height*gesture.camera.h*ratio,w:newWidth,h:gesture.camera.h*ratio};renderCamera();
  });
  function endPointer(event){pointers.delete(event.pointerId);if(pointers.size)startGesture();else{svg.classList.remove('dragging');gesture=null;setTimeout(()=>{dragMoved=false;},0);}}
  svg.addEventListener('pointerup',endPointer);svg.addEventListener('pointercancel',endPointer);
  // Modifier + wheel avoids trapping normal page scrolling.
  svg.addEventListener('wheel',event=>{if(event.ctrlKey||event.metaKey){event.preventDefault();zoom(Math.exp(-event.deltaY*.004),point(event.clientX,event.clientY));}},{passive:false});
  window.addEventListener('resize',fit);
  function selectStation(id,{scroll=false,locate=false,updateHash=true}={}) {
    const station=stations.get(id);if(!station)return;
    if(currentStation)markers.get(currentStation.id).classList.remove('selected');
    currentStation=station;markers.get(id).classList.add('selected');
    $('map-peek').hidden=true;
    currentPhotos=station.photos.map(file=>photos.get(file));photoIndex=0;
    $('station-title').textContent=station.name;
    const lines=station.routes.filter(r=>!r.startsWith('Green')).map(r=>routeNames.get(r).replace(' Line',''));
    const green=station.routes.filter(r=>r.startsWith('Green')).map(r=>r.replace('Green-',''));
    if(green.length)lines.push('Green '+green.join(' / '));
    $('station-lines').textContent=lines.join(' · ');
    $('locate-station').hidden=false;renderPhoto();
    if(updateHash)history.replaceState(null,'','#station='+encodeURIComponent(id));
    if(locate)locateStation();
    if(scroll)$('photo-card').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'nearest'});
  }
  function renderPhoto() {
    const p=currentPhotos[photoIndex];const img=$('station-photo');
    $('photo-open').hidden=!p;$('photo-open').disabled=!p;
    if(p){img.src=p.src;img.alt=`${currentStation.name} — ${p.file}`;$('photo-source').textContent=p.file;}
    else{img.removeAttribute('src');img.alt='';$('photo-source').textContent='';}
    $('photo-count').textContent=p?`${photoIndex+1} / ${currentPhotos.length}`:'';
    $('previous-photo').disabled=currentPhotos.length<2;$('next-photo').disabled=currentPhotos.length<2;
    $('photo-card').hidden=!p;
  }
  function showPeek(){
    const p=currentPhotos[photoIndex];$('peek-name').textContent=currentStation.name;
    $('peek-photo').disabled=!p;$('peek-image').hidden=!p;
    if(p){$('peek-image').src=p.thumb;$('peek-image').alt=currentStation.name+' — click to enlarge';}
    else $('peek-image').removeAttribute('src');
    $('peek-more').hidden=!p;
    $('map-peek').hidden=!p;
  }
  $('peek-close').onclick=()=>{$('map-peek').hidden=true;};
  $('peek-photo').onclick=()=>openLightbox(currentPhotos,photoIndex,currentStation.name);
  $('peek-more').onclick=()=>{$('map-peek').hidden=true;$('photo-card').scrollIntoView({behavior:'smooth',block:'center'});};
  function movePhoto(delta){if(!currentPhotos.length)return;photoIndex=(photoIndex+delta+currentPhotos.length)%currentPhotos.length;renderPhoto();}
  $('previous-photo').onclick=()=>movePhoto(-1);$('next-photo').onclick=()=>movePhoto(1);
  function locateStation(){const w=homeCamera.w/2.4;const h=w*homeCamera.h/homeCamera.w;camera={x:currentStation.x-w/2,y:currentStation.y-h/2,w,h};renderCamera();frame.scrollIntoView({behavior:'smooth',block:'center'});}
  $('locate-station').onclick=locateStation;
  const tripPhotos=data.photos.filter(p=>!p.station), gallery=$('trip-gallery');let galleryCount=0;
  // Start with portraits and views, then allow the complete between-stops collection.
  const highlightFiles=['P1010917.JPG','SAM_0644.JPG','P1010958.JPG','P1010828.JPG','P1010945.JPG','SAM_0690.JPG','P1010888.JPG','P1010930.JPG','SAM_0709.JPG'];
  tripPhotos.sort((a,b)=>{const ai=highlightFiles.indexOf(a.file),bi=highlightFiles.indexOf(b.file);return (ai<0?1000:ai)-(bi<0?1000:bi)||a.number-b.number;});
  function moreGallery(expand=false){const end=expand?tripPhotos.length:Math.min(3,tripPhotos.length);for(let i=galleryCount;i<end;i++){const p=tripPhotos[i],button=document.createElement('button'),img=document.createElement('img');img.src=p.thumb;img.alt=p.note;img.loading='lazy';img.width=320;img.height=220;button.setAttribute('aria-label',`Enlarge ${p.file}: ${p.note}`);button.append(img);button.onclick=()=>openLightbox(tripPhotos,i,'Between stops');gallery.append(button);}galleryCount=end;$('more-gallery').hidden=galleryCount>=tripPhotos.length;}
  $('more-gallery').onclick=()=>{moreGallery(true);$('more-gallery').setAttribute('aria-expanded','true');};
  const dialog=$('lightbox');
  function openLightbox(list,index,title){modalPhotos=list;modalIndex=index;modalTitle=title;renderLightbox();dialog.showModal();}
  function renderLightbox(){const p=modalPhotos[modalIndex];$('lightbox-title').textContent=modalTitle;$('lightbox-image').src=p.src;$('lightbox-image').alt=modalTitle+' — '+p.file;$('lightbox-caption').textContent=`${p.file} · ${modalIndex+1} / ${modalPhotos.length}`;$('lightbox-prev').disabled=modalPhotos.length<2;$('lightbox-next').disabled=modalPhotos.length<2;}
  function moveLightbox(delta){modalIndex=(modalIndex+delta+modalPhotos.length)%modalPhotos.length;renderLightbox();}
  $('photo-open').onclick=()=>openLightbox(currentPhotos,photoIndex,currentStation.name);
  $('close-lightbox').onclick=()=>dialog.close();$('lightbox-prev').onclick=()=>moveLightbox(-1);$('lightbox-next').onclick=()=>moveLightbox(1);
  dialog.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'){event.preventDefault();moveLightbox(-1);}if(event.key==='ArrowRight'){event.preventDefault();moveLightbox(1);}});
  dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
  dialog.addEventListener('close',()=>{$('lightbox-image').removeAttribute('src');});
  function readHash(){const id=new URLSearchParams(location.hash.slice(1)).get('station');selectStation(stations.has(id)?id:'place-pktrm',{updateHash:false});}
  window.addEventListener('hashchange',readHash);
  fit();moreGallery();readHash();
})();
