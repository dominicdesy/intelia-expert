# PWA Implementation - Progressive Web App

## Overview

Intelia Expert is now a Progressive Web App (PWA) that can be installed on mobile devices (iOS and Android) and desktop computers, providing an app-like experience with offline capabilities.

## Features

- ✅ **Installable on Android** - Native install prompt with automatic icon on home screen
- ✅ **Installable on iOS Safari** - Visual instructions banner for manual installation
- ✅ **Installable on Desktop** - Chrome, Edge, and other browsers
- ✅ **Offline Support** - Service worker caches assets for offline access
- ✅ **App-like Experience** - Runs in standalone mode without browser UI
- ✅ **Smart Prompts** - Only shows install prompts once every 7 days if dismissed

## How It Works

### Android / Desktop Chrome / Edge

When a user visits the site on Android or desktop Chrome/Edge:
1. Browser detects the PWA is installable (via manifest.json)
2. `beforeinstallprompt` event fires
3. `InstallPrompt` component shows a custom banner
4. User clicks "Installer"
5. Native browser prompt appears
6. App installs to home screen automatically

### iOS Safari

Since iOS doesn't support automatic PWA installation:
1. `IOSInstallBanner` detects iOS Safari
2. Shows visual instructions banner with 3 steps:
   - Tap Share button
   - Select "Add to Home Screen"
   - Tap "Add"
3. User follows manual steps
4. App icon appears on home screen

## Files Created

### Components

**`frontend/components/pwa/PWAManager.tsx`**
- Main PWA management component
- Registers service worker
- Renders install prompts

**`frontend/components/pwa/InstallPrompt.tsx`**
- Android/Desktop install prompt
- Listens for `beforeinstallprompt` event
- Shows custom banner with install button
- Dismissable (remembers for 7 days)

**`frontend/components/pwa/IOSInstallBanner.tsx`**
- iOS Safari-specific install banner
- Detects iOS Safari browser
- Shows visual step-by-step instructions
- Dismissable (remembers for 7 days)

### Service Worker

**`frontend/public/sw.js`**
- Caches static assets
- Network-first strategy for dynamic content
- Offline fallback support
- Auto-updates every hour

### Manifest

**`frontend/public/manifest.json`** (updated)
- App metadata (name, description, colors)
- Icon definitions (72px to 512px)
- Display mode: standalone
- Theme colors and orientation

### Styles

**`frontend/app/globals.css`** (updated)
- Added `@keyframes slide-up` animation
- `.animate-slide-up` class for banner entrance

### Layout

**`frontend/app/layout.tsx`** (updated)
- Imported and added `<PWAManager />` component
- Placed after Toaster, before closing MenuProvider

## Icon Requirements

The PWA requires app icons in multiple sizes. Place icons in `frontend/public/images/`:

- icon-72x72.png
- icon-96x96.png
- icon-128x128.png
- icon-144x144.png
- icon-152x152.png
- icon-192x192.png
- icon-384x384.png
- icon-512x512.png

**Current status**: Using `favicon.png` as fallback. Update `manifest.json` once proper icons are added.

## User Experience Flow

### First Visit
1. User lands on site
2. After 3 seconds (iOS) or immediately (Android), install prompt appears
3. User can install or dismiss

### Dismissal
- If dismissed, prompt won't show again for 7 days
- localStorage key: `pwa-install-dismissed` or `ios-install-dismissed`

### Already Installed
- Prompts automatically hide if app is already installed
- Detection via `display-mode: standalone` (Android) or `navigator.standalone` (iOS)

## Testing

### Test on Android
1. Open Chrome/Edge on Android device
2. Visit https://expert.intelia.com
3. Install banner should appear
4. Click "Installer"
5. App installs to home screen

### Test on iOS
1. Open Safari on iPhone/iPad
2. Visit https://expert.intelia.com
3. Wait 3 seconds
4. iOS install banner appears with instructions
5. Follow steps manually
6. App icon appears on home screen

### Test Dismissal
1. Dismiss the banner
2. Refresh page → banner should not appear
3. Clear localStorage
4. Refresh page → banner reappears

### Clear Dismissal (for testing)
```javascript
// In browser console
localStorage.removeItem('pwa-install-dismissed');
localStorage.removeItem('ios-install-dismissed');
location.reload();
```

## Service Worker Updates

The service worker:
- Caches assets on install
- Uses network-first strategy
- Falls back to cache when offline
- Auto-checks for updates every hour
- Self-updates on activation

To force update:
```javascript
// In browser console
navigator.serviceWorker.getRegistrations().then(regs => {
  regs.forEach(reg => reg.unregister());
});
location.reload();
```

## Browser Support

| Browser | Platform | Install Support | Notes |
|---------|----------|----------------|-------|
| Chrome | Android | ✅ Auto | Native prompt |
| Chrome | Desktop | ✅ Auto | Native prompt |
| Edge | Android | ✅ Auto | Native prompt |
| Edge | Desktop | ✅ Auto | Native prompt |
| Safari | iOS | ⚠️ Manual | Instructions banner |
| Safari | macOS | ❌ No | Not supported |
| Firefox | Android | ⚠️ Limited | Basic support |

## Troubleshooting

### Banner doesn't appear on Android
- Check browser console for errors
- Ensure manifest.json is accessible
- Verify service worker registered successfully
- Check if already installed (opens in standalone mode)

### iOS banner doesn't show
- Must be Safari (not Chrome/Firefox on iOS)
- Check if already installed (`navigator.standalone === true`)
- Clear localStorage to reset dismissal

### Service worker not registering
- Check browser console for errors
- Ensure HTTPS (required for service workers)
- Verify sw.js is accessible at /sw.js
- Check for syntax errors in sw.js

### App not updating
- Service workers cache aggressively
- Hard refresh: Ctrl+Shift+R (desktop) or clear cache (mobile)
- Unregister service worker and reload
- Update CACHE_NAME in sw.js to force update

## Future Enhancements

- [ ] Add proper app icons (72px to 512px)
- [ ] Add app screenshots for install prompt
- [ ] Implement background sync for offline actions
- [ ] Add push notifications support
- [ ] Track install conversion rate
- [ ] A/B test different banner designs
- [ ] Add "What's New" screen after updates
- [ ] Implement app shortcuts in manifest

## Metrics to Track

- Install rate (installs / unique visitors)
- Dismiss rate
- Reinstall rate (after dismissal)
- Platform distribution (iOS vs Android vs Desktop)
- Time to install (from first visit)
- Retention rate (7-day, 30-day)

## Security Considerations

- Service worker requires HTTPS
- Scope limited to origin
- No sensitive data cached
- Cache cleared on version update
- No cross-origin requests cached
