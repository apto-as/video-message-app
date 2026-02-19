#!/usr/bin/env node
/**
 * PWA Icon Generator
 * Generates PNG icons for the Video Message App PWA.
 * Uses only Node.js built-in modules (no external dependencies).
 *
 * Usage: node scripts/generate-pwa-icons.js
 */
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

// CRC32 lookup table
const crc32Table = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  let c = i;
  for (let j = 0; j < 8; j++) {
    c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
  }
  crc32Table[i] = c;
}

function crc32(buf) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < buf.length; i++) {
    crc = crc32Table[(crc ^ buf[i]) & 0xFF] ^ (crc >>> 8);
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

function createChunk(type, data) {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  const typeBuffer = Buffer.from(type, 'ascii');
  const crcInput = Buffer.concat([typeBuffer, data]);
  const crcBuf = Buffer.alloc(4);
  crcBuf.writeUInt32BE(crc32(crcInput), 0);
  return Buffer.concat([length, typeBuffer, data, crcBuf]);
}

function createPNG(width, height, pixels) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8;  // bit depth
  ihdrData[9] = 6;  // RGBA
  ihdrData[10] = 0; // compression
  ihdrData[11] = 0; // filter
  ihdrData[12] = 0; // interlace
  const ihdr = createChunk('IHDR', ihdrData);

  // Raw scanlines: filter-byte + RGBA per pixel per row
  const rawData = Buffer.alloc(height * (1 + width * 4));
  for (let y = 0; y < height; y++) {
    const rowOff = y * (1 + width * 4);
    rawData[rowOff] = 0; // no filter
    for (let x = 0; x < width; x++) {
      const pi = (y * width + x) * 4;
      const di = rowOff + 1 + x * 4;
      rawData[di] = pixels[pi];
      rawData[di + 1] = pixels[pi + 1];
      rawData[di + 2] = pixels[pi + 2];
      rawData[di + 3] = pixels[pi + 3];
    }
  }
  const compressed = zlib.deflateSync(rawData, { level: 9 });
  const idat = createChunk('IDAT', compressed);
  const iend = createChunk('IEND', Buffer.alloc(0));

  return Buffer.concat([signature, ihdr, idat, iend]);
}

function drawIcon(size, maskable) {
  const pixels = new Uint8Array(size * size * 4);
  const cx = size / 2;
  const cy = size / 2;
  const bgR = 0, bgG = 123, bgB = 255; // #007bff

  // Play triangle (relative coordinates)
  const triLeftX  = 0.38;
  const triRightX = 0.72;
  const triTopY   = 0.28;
  const triBotY   = 0.72;
  const triCY     = 0.50;

  const circleRadius = maskable ? size * 0.5 : size * 0.45;
  const aa = Math.max(1, size * 0.008); // anti-alias edge width

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const idx = (y * size + x) * 4;
      const dx = x - cx;
      const dy = y - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);

      // Circle coverage (0..1)
      let circleCov = Math.min(1, Math.max(0, (circleRadius - dist) / aa));

      if (maskable && dist > circleRadius) {
        // Full-bleed background for maskable
        circleCov = 1;
      }

      if (circleCov <= 0) {
        pixels[idx] = 0;
        pixels[idx + 1] = 0;
        pixels[idx + 2] = 0;
        pixels[idx + 3] = 0;
        continue;
      }

      // Normalised coords
      const nx = x / size;
      const ny = y / size;

      // Check if inside play triangle
      let inTriangle = false;
      if (nx >= triLeftX && nx <= triRightX) {
        const progress = (nx - triLeftX) / (triRightX - triLeftX);
        const halfH = ((triBotY - triTopY) / 2) * (1 - progress);
        if (ny >= triCY - halfH && ny <= triCY + halfH) {
          inTriangle = true;
        }
      }

      const alpha = Math.round(255 * circleCov);
      if (inTriangle) {
        pixels[idx] = 255;
        pixels[idx + 1] = 255;
        pixels[idx + 2] = 255;
        pixels[idx + 3] = alpha;
      } else {
        pixels[idx] = bgR;
        pixels[idx + 1] = bgG;
        pixels[idx + 2] = bgB;
        pixels[idx + 3] = alpha;
      }
    }
  }
  return pixels;
}

// --- Main ---
const iconsDir = path.join(__dirname, '..', 'frontend', 'public', 'icons');
fs.mkdirSync(iconsDir, { recursive: true });

const specs = [
  { size: 180, name: 'apple-touch-icon.png', maskable: false },
  { size: 192, name: 'icon-192.png',         maskable: false },
  { size: 512, name: 'icon-512.png',         maskable: false },
  { size: 192, name: 'icon-maskable-192.png', maskable: true },
  { size: 512, name: 'icon-maskable-512.png', maskable: true },
];

specs.forEach(({ size, name, maskable }) => {
  process.stdout.write(`Generating ${name} (${size}x${size})... `);
  const pixels = drawIcon(size, maskable);
  const png = createPNG(size, size, pixels);
  fs.writeFileSync(path.join(iconsDir, name), png);
  console.log(`${(png.length / 1024).toFixed(1)} KB`);
});

// Copy apple-touch-icon to public root for <link rel="apple-touch-icon">
fs.copyFileSync(
  path.join(iconsDir, 'apple-touch-icon.png'),
  path.join(__dirname, '..', 'frontend', 'public', 'apple-touch-icon.png')
);
console.log('Copied apple-touch-icon.png to public/');
console.log('Done!');
