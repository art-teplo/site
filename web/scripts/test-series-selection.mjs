import assert from 'node:assert/strict';
import { test } from 'node:test';
import { executionAtDepth, seriesPrice, shouldFetchSelected, chooseExecution, queryWithExecution } from '../src/lib/series-selection.ts';

test('depth change retains the same factory connection and mounting', () => {
  const left={key:'left1',tubes:1,connection:'bottom_center',thermovalve:false,mount:'wall',sourceId:'22712'};
  const right={...left,key:'right1',sourceId:'22713'};
  const left2={...left,key:'left2',tubes:2};
  const right2={...right,key:'right2',tubes:2};
  assert.equal(executionAtDepth([left,right,left2,right2],right,2)?.key,'right2');
});

test('any RAL and unresolved quotes never display a numeric amount', () => {
  assert.equal(seriesPrice({anyRal:true,stale:null,priceFrom:296}),null);
  assert.equal(seriesPrice({anyRal:false,stale:'pending',selectedPrice:296,priceFrom:459}),null);
  assert.equal(seriesPrice({anyRal:false,stale:'failed',selectedPrice:296}),null);
  assert.equal(seriesPrice({anyRal:false,stale:null,selectedPrice:null,priceFrom:459}),null);
  assert.equal(seriesPrice({anyRal:false,stale:null,priceFrom:459}),459);
});

test('a selected article is fetched even with zero colour-filtered rows', () => {
  assert.equal(shouldFetchSelected({article:'SKU',pending:false,inRows:false}),true);
  assert.equal(shouldFetchSelected({article:'SKU',pending:true,inRows:false}),false);
});

test('changing configuration clears conflicting controls but preserves position size colour and article',()=>{
  const query={execution:'old',v:'SKU',color:'RAL',ranges:{height:[500,500]},lists:{orientation:['h'],mount:['wall'],thermovalve:['false'],connection:['side']}};
  const next=queryWithExecution(query,'new');
  assert.deepEqual(next,{...query,execution:'new',lists:{orientation:['h']}});
  assert.deepEqual(query.lists.mount,['wall']);
});

test('a depth change preserves known valve and mount when factory codes differ',()=>{
  const current={key:'old',tubes:1,connection:'bottom_right',mount:'wall',thermovalve:true,sourceId:'1118'};
  const side={...current,key:'side',tubes:2,connection:'side',thermovalve:false,sourceId:'1117'};
  const lower={...current,key:'lower',tubes:2,connection:'bottom_universal',sourceId:'1120'};
  assert.equal(chooseExecution([side,lower],current,{tubes:2})?.key,'lower');
  assert.equal(chooseExecution([side,lower],current,{mount:'floor'}),undefined);
});

test('initial execution preserves explicit legacy keys and independent restrictions',async()=>{
  const { initialExecution }=await import('../src/lib/series-selection.ts');
  const entries=[{key:'side',connection:'side',tubes:2,mount:'wall',thermovalve:false}];
  assert.equal(initialExecution({execution:'2-side',lists:{},ranges:{}},'side',entries),'2-side');
  assert.equal(initialExecution({lists:{connection:['bottom_center']},ranges:{}},'side',entries),undefined);
});

test('card navigation retains applied offer restrictions and pending prices are hidden',async()=>{
 const { offerNavigation, tablePrice }=await import('../src/lib/series-selection.ts');
 const p=offerNavigation('connection=bottom_center&color=black&page=3&brand=kzto&height_min=500&v=OLD');
 assert.equal(p.get('connection'),'bottom_center');assert.equal(p.get('color'),'black');assert.equal(p.has('page'),false);assert.equal(p.has('v'),false);
 assert.equal(tablePrice(640,'pending',false),null);assert.equal(tablePrice(640,'failed',false),null);assert.equal(tablePrice(640,null,false),640);
});

test('gallery overflow puts the counter on sixth preview for every brand',async()=>{
 const {thumbnailWindow}=await import('../src/lib/gallery-preview.ts');
 assert.deepEqual(thumbnailWindow([1,2,3,4,5,6]),{visible:[1,2,3,4,5,6],hidden:[]});
 assert.deepEqual(thumbnailWindow([1,2,3,4,5,6,7,8]),{visible:[1,2,3,4,5],hidden:[6,7,8]});
});

test('gallery prioritizes the selected color and keeps admin order within each priority', async () => {
  const { orderGalleryPhotos } = await import('../src/lib/series-color.ts');
  assert.equal(typeof orderGalleryPhotos, 'function');
  const photos = [
    { src: 'other', color: '9005', orientation: 'h' },
    { src: 'generic-first', color: null, orientation: 'h' },
    { src: 'matching-base', color: '1015', orientation: 'h' },
    { src: 'generic-second', color: null, orientation: 'v' },
    { src: 'matching-first', color: '1015 глянец', orientation: 'v' },
    { src: 'matching-second', color: '1015 глянец', orientation: 'h' },
    { src: 'matching-first', color: null, orientation: '' },
  ];
  assert.deepEqual(orderGalleryPhotos(photos, '1015 глянец').map(({ src }) => src), [
    'matching-first', 'matching-second', 'matching-base', 'other', 'generic-first', 'generic-second',
  ]);
  assert.deepEqual(orderGalleryPhotos(photos).map(({ src }) => src), [
    'other', 'generic-first', 'matching-base', 'generic-second', 'matching-first', 'matching-second',
  ]);
  assert.deepEqual(orderGalleryPhotos(photos, '9001'), orderGalleryPhotos(photos));
});

test('showcase links carry active catalog filters without injecting dimensions or photo orientation', async () => {
  const { showcaseQuery } = await import('../src/lib/series-selection.ts');
  assert.equal(showcaseQuery('').toString(), '');
  assert.equal(
    showcaseQuery('height_min=500&height_max=700&orientation=v&color=white&page=2&o=h').toString(),
    'height_min=500&height_max=700&orientation=v&color=white',
  );
});

test('legacy edition links retain the requested height and explicitly selected article', async () => {
  const { showcaseQuery } = await import('../src/lib/series-selection.ts');
  assert.equal(showcaseQuery('h=1200&color=white&v=OLD&o=h', 'SKU').toString(), 'h=1200&color=white&v=SKU');
  assert.equal(showcaseQuery('', 'SKU').toString(), 'v=SKU');
});
