---
name: asset-and-image-optimization
description: Optimize images and static assets to reduce page weight, improve LCP, and eliminate CLS from unsized media.
discipline: frontend
tags: [images, performance, cdn, webp, lazy-loading]
---

# Asset and Image Optimization

## When to use
Apply this skill when images are the LCP element, when Lighthouse flags "Serve images in next-gen formats" or "Properly size images", when page weight is dominated by images (check Network panel), or when layout shifts are traced to images without explicit dimensions.

## Signal
- Lighthouse "Serve images in next-gen formats" or "Efficiently encode images" warnings.
- `<img>` elements without `width` and `height` attributes causing CLS.
- Images served larger than their display size (e.g., 2000 px image displayed at 400 px).
- No `loading="lazy"` on below-fold images (unnecessary network load on initial page view).
- `loading="lazy"` applied to the LCP image (delays the most important paint).
- SVGs not compressed — raw Illustrator exports with metadata and redundant paths.
- No CDN in front of the origin server — images served from origin on every request.

## Why
Unoptimized images are the single largest cause of poor LCP scores and excessive page weight. Images typically account for 50–70% of total bytes transferred on image-heavy pages. CLS caused by unsized images is the easiest CLS to fix and the most common. Modern formats (WebP, AVIF) deliver equivalent visual quality at 25–50% smaller file sizes compared to JPEG/PNG.

## Remediate

1. **Use modern image formats.** Convert images to AVIF (50% smaller than JPEG) or WebP (25–35% smaller) using `<picture>` with fallback:
   ```html
   <picture>
     <source type="image/avif" srcset="/hero.avif">
     <source type="image/webp" srcset="/hero.webp">
     <img src="/hero.jpg" alt="Hero image" width="1200" height="630">
   </picture>
   ```
   All major browsers support WebP; AVIF has >95% browser coverage as of 2025.

2. **Use Next.js `<Image>` component.** When using Next.js, replace every `<img>` with `next/image`. It automatically handles: WebP/AVIF conversion, responsive `srcset`, lazy loading, explicit sizing to prevent CLS, and priority loading for LCP images:
   ```tsx
   import Image from 'next/image';
   // LCP image — add priority
   <Image src="/hero.jpg" alt="Hero" width={1200} height={630} priority />
   // Below-fold image — lazy loaded by default
   <Image src="/card.jpg" alt="Card" width={400} height={300} />
   ```

3. **Always specify `width` and `height`.** Every `<img>` must have both attributes so the browser reserves space before the image loads, eliminating CLS. When using CSS `max-width: 100%`, combine with CSS `aspect-ratio`:
   ```css
   img { width: 100%; aspect-ratio: 16 / 9; }
   ```

4. **Lazy-load below-fold images.** Add `loading="lazy"` to every image not visible on initial viewport. Never apply it to the LCP image — this delays the most critical paint:
   ```html
   <!-- Never lazy-load LCP image -->
   <img src="/hero.jpg" alt="Hero" width="1200" height="630" fetchpriority="high">
   <!-- Lazy-load everything else -->
   <img src="/card.jpg" alt="Card" width="400" height="300" loading="lazy">
   ```

5. **Serve via CDN with image transformation.** Use Cloudflare Images, Cloudinary, Imgix, or AWS CloudFront + Lambda@Edge to dynamically resize and convert images at the edge. This avoids storing multiple versions and serves the correct size for each device:
   ```
   https://cdn.example.com/hero.jpg?w=800&format=webp&q=80
   ```

6. **Generate responsive `srcset`.** Serve different sizes for different viewports:
   ```html
   <img
     srcset="/hero-400.webp 400w, /hero-800.webp 800w, /hero-1200.webp 1200w"
     sizes="(max-width: 600px) 400px, (max-width: 1024px) 800px, 1200px"
     src="/hero-1200.webp"
     alt="Hero"
     width="1200"
     height="630"
   >
   ```

7. **Compress SVGs with SVGO.** Raw SVG exports from Figma/Illustrator contain metadata, comments, and redundant paths. Run `svgo --multipass` to reduce SVG file size by 40–70%:
   ```sh
   npx svgo --multipass icons/*.svg
   ```

8. **Preload the LCP image.** Add a `<link rel="preload">` in `<head>` for the LCP image to start loading before the browser parses the `<img>` element in the body:
   ```html
   <link rel="preload" as="image" href="/hero.webp" fetchpriority="high">
   ```

9. **Compress raster images before upload.** Use `sharp` (Node.js) or `squoosh` for batch compression. Target JPEG quality 75–85 and WebP quality 80. Lossless PNG compression via `pngquant` or `oxipng`.

## References
- web.dev/fast/use-imagemin-to-compress-images
- Next.js Image Optimization documentation
- AVIF format specification (AOMedia)
- Cloudinary / Imgix image transformation APIs
- SVGO (svg/svgo on GitHub)
