/* Optional maintainer tool. The published site needs no dependencies. */
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
const root = path.resolve(__dirname, '..');
const source = process.argv[2];
if (!source) { console.error('Usage: node scripts/prepare-photos.cjs /path/to/extracted/images'); process.exit(1); }
(async () => {
  const inventory = JSON.parse(fs.readFileSync(path.join(root, 'review/photo-inventory.json')));
  const photos = path.join(root, 'site/assets/photos');
  fs.mkdirSync(photos, {recursive: true});
  for (const photo of inventory) {
    const input = path.join(source, photo.file);
    const stem = path.parse(photo.file).name;
    let pipeline = sharp(input).rotate();
    // This camera shot was saved sideways without a useful orientation tag.
    if (photo.file === 'SAM_0690.JPG') pipeline = pipeline.rotate(90);
    await pipeline.clone().resize({width: 1440, height: 1440, fit: 'inside', withoutEnlargement: true}).webp({quality: 83}).toFile(path.join(photos, stem + '.webp'));
    await pipeline.clone().resize(320, 220, {fit: 'inside', withoutEnlargement: true}).webp({quality: 75}).toFile(path.join(photos, stem + '-thumb.webp'));
  }
  console.log(`Prepared ${inventory.length} photos. Originals remain untouched.`);
})().catch(error => {console.error(error); process.exit(1);});
