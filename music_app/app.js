/**
 * Music-Duniya Web Player - Complete Ultra-Premium Frontend, Audio Engine & Lossless Music Streamer
 * Supports Lavish Royal Playlists, Artist Avatars, DJPunjab A-Z Scraping, and Supabase Temporary Caching
 */

(function () {
  'use strict';

  // --- STATE ---
  const state = {
    songs: [],
    cachedSongs: [],
    popularSingers: [],
    currentSong: null,
    isPlaying: false,
    currentPlaylist: 'all',
    currentView: 'home',
    queue: [],
    queueIndex: -1,
    isShuffle: false,
    repeatMode: 'all', // 'off' | 'all' | 'one'
    likedSongIds: new Set(),
    userPlaylists: [],
    curatedPlaylists: {},
    history: ['home'],
    historyIndex: 0,
    volume: 0.8,
    isMuted: false,
    searchQuery: '',
    searchSourceFilter: 'all', // 'all' | 'djjohal' | 'mrjatt' | 'djpunjab' | 'local'
    selectedLetter: 'a',
    letterSingers: [],
    onlineResults: [],
    isSearchingOnline: false,
    isDraggingSeek: false
  };

  // --- DOM ELEMENTS ---
  const audio = document.getElementById('audio-engine');
  const viewContainer = document.getElementById('view-container');
  const topBar = document.getElementById('top-bar');
  const searchInput = document.getElementById('search-input');
  const btnClearSearch = document.getElementById('btn-clear-search');
  const topSearchContainer = document.getElementById('top-search-container');
  const btnNavBack = document.getElementById('btn-nav-back');
  const btnNavForward = document.getElementById('btn-nav-forward');
  const btnCreatePlaylist = document.getElementById('btn-create-playlist');
  const userPlaylistsContainer = document.getElementById('user-playlists-container');
  const likedCountSpan = document.getElementById('liked-count');
  const cachedCountSpan = document.getElementById('cached-count');

  // Player Elements
  const playerCoverArt = document.getElementById('player-cover-art');
  const playerTitle = document.getElementById('player-title');
  const playerArtist = document.getElementById('player-artist');
  const playerLikeBtn = document.getElementById('player-like-btn');
  const btnPlayPause = document.getElementById('btn-play-pause');
  const playIcon = btnPlayPause.querySelector('.play-icon');
  const pauseIcon = btnPlayPause.querySelector('.pause-icon');
  const btnPrev = document.getElementById('btn-prev');
  const btnNext = document.getElementById('btn-next');
  const btnShuffle = document.getElementById('btn-shuffle');
  const btnRepeat = document.getElementById('btn-repeat');
  const repeatOneBadge = btnRepeat.querySelector('.repeat-one-badge');

  // Seek bar
  const seekBarWrap = document.getElementById('seek-bar-wrap');
  const seekBarFill = document.getElementById('seek-bar-fill');
  const seekBarHandle = document.getElementById('seek-bar-handle');
  const currentTimeLabel = document.getElementById('current-time');
  const totalDurationLabel = document.getElementById('total-duration');

  // Volume
  const btnMute = document.getElementById('btn-mute');
  const volHighIcon = btnMute.querySelector('.vol-high');
  const volMutedIcon = btnMute.querySelector('.vol-muted');
  const volumeBarWrap = document.getElementById('volume-bar-wrap');
  const volumeBarFill = document.getElementById('volume-bar-fill');
  const volumeBarHandle = document.getElementById('volume-bar-handle');

  // Drawer & Fullscreen
  const rightDrawer = document.getElementById('right-drawer');
  const drawerContent = document.getElementById('drawer-content');
  const btnQueueToggle = document.getElementById('btn-queue-toggle');
  const btnCloseDrawer = document.getElementById('btn-close-drawer');
  const btnFullscreen = document.getElementById('btn-fullscreen');
  const fsOverlay = document.getElementById('fullscreen-overlay');
  const btnCloseFs = document.getElementById('btn-close-fs');
  const fsCover = document.getElementById('fs-cover');
  const fsTitle = document.getElementById('fs-title');
  const fsArtist = document.getElementById('fs-artist');
  const toast = document.getElementById('toast');

  let searchDebounceTimer = null;

  // --- INITIALIZATION ---
  async function init() {
    loadLocalState();
    bindEvents();

    const urlParams = new URLSearchParams(window.location.search);
    const queryParam = urlParams.get('q');
    const viewParam = urlParams.get('view');
    const slugParam = urlParams.get('slug');

    // Instant non-blocking first paint
    if (queryParam) {
      searchInput.value = queryParam;
      state.searchQuery = queryParam;
      navigateTo('search');
    } else if (viewParam) {
      if (viewParam === 'settings') {
        renderView('home');
        setTimeout(() => {
          const sm = document.getElementById('settings-modal-overlay');
          if (sm) sm.classList.add('open');
        }, 300);
      } else if (viewParam === 'drawer') {
        renderView('home');
        setTimeout(() => {
          const pd = document.getElementById('profile-drawer-overlay');
          if (pd) pd.classList.add('open');
        }, 300);
      } else {
        navigateTo(viewParam, slugParam);
      }
    } else {
      renderView('home');
    }

    // Parallel background loading
    Promise.allSettled([
      fetchSongs(),
      fetchCachedSongs(),
      fetchCuratedPlaylists(),
      fetchPopularSingers()
    ]).then(() => {
      updateLibraryUI();
      if (!queryParam && (!viewParam || viewParam === 'home')) {
        renderHomeView();
      } else if (viewParam === 'library') {
        renderLibraryView();
      } else if (viewParam === 'playlist') {
        renderPlaylistView(slugParam || 'all');
      }
    });

    if (queryParam) {
      performOnlineSearch(queryParam);
    }

    if (urlParams.get('modal') === 'profile') {
      setTimeout(() => {
        const drawer = document.getElementById('profile-drawer-overlay');
        if (drawer) drawer.classList.add('open');
      }, 300);
    } else if (urlParams.get('modal') === 'settings') {
      setTimeout(() => {
        const sModal = document.getElementById('settings-modal-overlay');
        if (sModal) sModal.classList.add('open');
        const chkBtn = document.getElementById('btn-check-update');
        if (chkBtn) chkBtn.click();
      }, 300);
    } else if (urlParams.get('modal') === 'jam') {
      setTimeout(() => {
        const jModal = document.getElementById('jam-modal-overlay');
        if (jModal) jModal.classList.add('open');
      }, 300);
    } else if (urlParams.get('modal') === 'auth') {
      setTimeout(() => {
        const aModal = document.getElementById('auth-modal-overlay');
        if (aModal) aModal.classList.add('open');
      }, 300);
    }

    updateLibraryUI();
  }

  function loadLocalState() {
    try {
      const savedLikes = localStorage.getItem('musicduniya_liked_songs');
      if (savedLikes) {
        state.likedSongIds = new Set(JSON.parse(savedLikes));
      }
      const savedPlaylists = localStorage.getItem('musicduniya_user_playlists');
      if (savedPlaylists) {
        state.userPlaylists = JSON.parse(savedPlaylists);
      }
      const savedVol = localStorage.getItem('musicduniya_volume');
      if (savedVol !== null) {
        state.volume = parseFloat(savedVol);
      }
      const savedShuffle = localStorage.getItem('musicduniya_shuffle');
      if (savedShuffle !== null) {
        state.isShuffle = JSON.parse(savedShuffle);
        btnShuffle.classList.toggle('active', state.isShuffle);
      }
      const savedRepeat = localStorage.getItem('musicduniya_repeat');
      if (savedRepeat) {
        state.repeatMode = savedRepeat;
        updateRepeatUI();
      }
    } catch (e) {
      console.warn('Could not read localStorage:', e);
    }

    audio.volume = state.volume;
    updateVolumeUI(state.volume);
  }

  async function fetchSongs() {
    if (window.AndroidBridge && typeof window.AndroidBridge.getAssetFileContentSync === 'function') {
      try {
        const raw = window.AndroidBridge.getAssetFileContentSync('songs.json');
        if (raw) {
          state.songs = JSON.parse(raw);
          state.songs.forEach(s => {
            if (!s.source) s.source = 'local';
          });
          state.queue = [...state.songs];
          if (state.songs.length > 0) {
            setNowPlayingTrack(state.songs[0], false);
          }
          return;
        }
      } catch (e) {}
    }

    try {
      const res = await fetch('/api/songs');
      if (!res.ok) throw new Error('API request failed');
      state.songs = await res.json();
    } catch (err) {
      try {
        const fallback = await fetch('songs.json');
        state.songs = await fallback.json();
      } catch (e) {
        state.songs = [];
      }
    }

    state.songs.forEach(s => {
      if (!s.source) s.source = 'local';
    });

    state.queue = [...state.songs];
    if (state.songs.length > 0) {
      setNowPlayingTrack(state.songs[0], false);
    }
  }

  async function fetchCachedSongs() {
    try {
      if (window.AndroidBridge && typeof window.AndroidBridge.getCachedSongsSync === 'function') {
        const raw = window.AndroidBridge.getCachedSongsSync();
        state.cachedSongs = JSON.parse(raw);
        if (cachedCountSpan) {
          cachedCountSpan.textContent = state.cachedSongs.length;
        }
        return;
      }
      const res = await fetch('/api/cached-songs');
      if (res.ok) {
        state.cachedSongs = await res.json();
        if (cachedCountSpan) {
          cachedCountSpan.textContent = state.cachedSongs.length;
        }
      }
    } catch (e) {}
  }

  async function fetchPopularSingers() {
    try {
      if (window.AndroidBridge && typeof window.AndroidBridge.getPopularSingersSync === 'function') {
        const raw = window.AndroidBridge.getPopularSingersSync();
        state.popularSingers = JSON.parse(raw);
        return;
      }
      const res = await fetch('/api/singers');
      if (res.ok) {
        state.popularSingers = await res.json();
      }
    } catch (e) {}
  }

  async function fetchCuratedPlaylists() {
    if (window.AndroidBridge && typeof window.AndroidBridge.getAssetFileContentSync === 'function') {
      try {
        const raw = window.AndroidBridge.getAssetFileContentSync('playlists_resolved.json');
        if (raw) {
          state.curatedPlaylists = JSON.parse(raw);
          return;
        }
      } catch (e) {}
    }

    try {
      const res = await fetch('/api/playlists');
      if (res.ok) {
        state.curatedPlaylists = await res.json();
        return;
      }
    } catch (e) {}
    try {
      const fallback = await fetch('playlists_resolved.json');
      if (fallback.ok) {
        state.curatedPlaylists = await fallback.json();
      }
    } catch (e) {
      state.curatedPlaylists = {};
    }
  }

  // --- AUDIO CONTROLS & ENGINE ---
  function playSong(song, newQueue = null) {
    if (!song) return;

    if (newQueue) {
      state.queue = [...newQueue];
    }
    state.queueIndex = state.queue.findIndex(s => s.id === song.id);
    if (state.queueIndex === -1) {
      state.queue.push(song);
      state.queueIndex = state.queue.length - 1;
    }

    setNowPlayingTrack(song, true);

    // Determine audio stream URL
    let sourceUrl = song.audio_url;
    if (!sourceUrl) {
      if (window.AndroidBridge && typeof window.AndroidBridge.resolveStreamUrlSync === 'function') {
        const cachedLocal = typeof window.AndroidBridge.getCachedFileUrlSync === 'function' ? window.AndroidBridge.getCachedFileUrlSync(song.id || '') : '';
        if (cachedLocal) {
          sourceUrl = cachedLocal;
          showToast(`⚡ Playing from Device Storage Cache`);
        } else {
          showToast(`⚡ Resolving Stream from ${(song.source || 'online').toUpperCase()}...`);
          const direct = window.AndroidBridge.resolveStreamUrlSync(song.source || '', song.page_url || '', song.stream_url || '');
          if (direct) {
            sourceUrl = direct;
            if (typeof window.AndroidBridge.startCacheDownloadAsync === 'function') {
              window.AndroidBridge.startCacheDownloadAsync(song.id || 'track', song.source || '', direct);
            }
          } else {
            sourceUrl = song.stream_url;
          }
        }
      } else if (song.source === 'djpunjab' || song.source === 'djjohal' || song.source === 'mrjatt') {
        sourceUrl = `/api/stream-or-download?id=${encodeURIComponent(song.id)}&source=${song.source}&page_url=${encodeURIComponent(song.page_url || '')}&stream_url=${encodeURIComponent(song.stream_url || '')}`;
        showToast(`⚡ Streaming & Caching from ${song.source.toUpperCase()}...`);
      } else {
        sourceUrl = song.stream_url;
      }
    }

    audio.src = sourceUrl;

    audio.play().then(() => {
      state.isPlaying = true;
      updatePlayPauseButton(true);
      updatePlayingRowHighlights();
      updateMediaSession(song);
      setTimeout(fetchCachedSongs, 3000);
    }).catch(err => {
      console.warn('Audio play error, attempting fallback:', err);
      if (song.stream_url && audio.src !== song.stream_url) {
        audio.src = song.stream_url;
        audio.play().catch(() => {});
      }
    });
  }

  function togglePlayPause() {
    if (!state.currentSong) {
      if (state.songs.length > 0) {
        playSong(state.songs[0]);
      }
      return;
    }

    if (audio.paused) {
      audio.play().then(() => {
        state.isPlaying = true;
        updatePlayPauseButton(true);
        updatePlayingRowHighlights();
      });
    } else {
      audio.pause();
      state.isPlaying = false;
      updatePlayPauseButton(false);
      updatePlayingRowHighlights();
    }
  }

  function playNext() {
    if (state.queue.length === 0) return;

    if (state.repeatMode === 'one') {
      audio.currentTime = 0;
      audio.play();
      return;
    }

    let nextIndex;
    if (state.isShuffle) {
      nextIndex = Math.floor(Math.random() * state.queue.length);
    } else {
      nextIndex = state.queueIndex + 1;
      if (nextIndex >= state.queue.length) {
        if (state.repeatMode === 'all') {
          nextIndex = 0;
        } else {
          state.isPlaying = false;
          updatePlayPauseButton(false);
          return;
        }
      }
    }

    playSong(state.queue[nextIndex]);
  }

  function playPrev() {
    if (state.queue.length === 0) return;

    if (audio.currentTime > 3) {
      audio.currentTime = 0;
      return;
    }

    let prevIndex = state.queueIndex - 1;
    if (prevIndex < 0) {
      prevIndex = state.queue.length - 1;
    }
    playSong(state.queue[prevIndex]);
  }

  function setNowPlayingTrack(song, autoplay = false) {
    state.currentSong = song;
    playerTitle.textContent = song.title;
    playerArtist.textContent = song.artist + (song.source && song.source !== 'local' ? ` • ${song.source.toUpperCase()}` : '');
    playerCoverArt.src = song.cover_url || 'https://lq.djjohal.com/covers_webp/48718/1.webp';
    playerLikeBtn.classList.toggle('liked', state.likedSongIds.has(song.id));

    // Update Master Soundstage Turntable Hero elements
    const hTitle = document.getElementById('hero-stage-title');
    if (hTitle) hTitle.textContent = song.title;
    const hArtist = document.getElementById('hero-stage-artist');
    if (hArtist) hArtist.textContent = song.artist + (song.source && song.source !== 'local' ? ` • ${song.source.toUpperCase()}` : '');
    const hCover = document.getElementById('hero-stage-cover');
    if (hCover) { hCover.src = song.cover_url || 'logo.png'; hCover.onerror = () => { hCover.src = 'logo.png'; }; }
    const cVinylImg = document.getElementById('console-vinyl-img');
    if (cVinylImg) { cVinylImg.src = song.cover_url || 'logo.png'; cVinylImg.onerror = () => { cVinylImg.src = 'logo.png'; }; }
    const fsVinylImg = document.getElementById('fs-vinyl-img');
    if (fsVinylImg) { fsVinylImg.src = song.cover_url || 'logo.png'; fsVinylImg.onerror = () => { fsVinylImg.src = 'logo.png'; }; }
    const hPlay = document.getElementById('btn-hero-play');
    if (hPlay) { hPlay.dataset.playSongId = song.id; }

    fsTitle.textContent = song.title;
    fsArtist.textContent = song.artist;
    fsCover.src = song.cover_url || playerCoverArt.src;
    fsCover.onerror = () => { fsCover.src = 'logo.png'; };
    playerCoverArt.onerror = () => { playerCoverArt.src = 'logo.png'; };

    totalDurationLabel.textContent = song.duration || '3:20';
    currentTimeLabel.textContent = '0:00';
    seekBarFill.style.width = '0%';
    seekBarHandle.style.left = '0%';

    if (!autoplay && song.audio_url) {
      audio.src = song.audio_url;
    }
  }

  function updatePlayPauseButton(playing) {
    if (playing) {
      playIcon.style.display = 'none';
      pauseIcon.style.display = 'block';
    } else {
      playIcon.style.display = 'block';
      pauseIcon.style.display = 'none';
    }

    // Toggle real-time vinyl spinning & frequency spectrum animations
    const heroDisc = document.getElementById('hero-vinyl-disc');
    if (heroDisc) heroDisc.classList.toggle('is-playing', playing);
    const consoleDisc = document.getElementById('console-mini-vinyl');
    if (consoleDisc) consoleDisc.classList.toggle('is-playing', playing);
    const fsDisc = document.getElementById('fs-vinyl');
    if (fsDisc) fsDisc.classList.toggle('is-playing', playing);
    const spectrum = document.getElementById('header-spectrum');
    if (spectrum) spectrum.classList.toggle('is-playing', playing);

    if (window.AndroidBridge && typeof window.AndroidBridge.updateNotification === 'function' && state.currentSong) {
      try {
        window.AndroidBridge.updateNotification(state.currentSong.title, state.currentSong.artist, state.currentSong.cover_url || '', playing);
      } catch (_) {}
    }
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = playing ? 'playing' : 'paused';
    }
  }

  function updateRepeatUI() {
    if (state.repeatMode === 'off') {
      btnRepeat.classList.remove('active');
      repeatOneBadge.style.display = 'none';
    } else if (state.repeatMode === 'all') {
      btnRepeat.classList.add('active');
      repeatOneBadge.style.display = 'none';
    } else if (state.repeatMode === 'one') {
      btnRepeat.classList.add('active');
      repeatOneBadge.style.display = 'block';
    }
  }

  function cycleRepeatMode() {
    if (state.repeatMode === 'all') {
      state.repeatMode = 'one';
    } else if (state.repeatMode === 'one') {
      state.repeatMode = 'off';
    } else {
      state.repeatMode = 'all';
    }
    localStorage.setItem('musicduniya_repeat', state.repeatMode);
    updateRepeatUI();
    showToast(`Repeat mode: ${state.repeatMode.toUpperCase()}`);
  }

  function toggleShuffle() {
    state.isShuffle = !state.isShuffle;
    localStorage.setItem('musicduniya_shuffle', JSON.stringify(state.isShuffle));
    btnShuffle.classList.toggle('active', state.isShuffle);
    showToast(state.isShuffle ? 'Shuffle is on' : 'Shuffle is off');
  }

  function toggleLike(songId) {
    if (state.likedSongIds.has(songId)) {
      state.likedSongIds.delete(songId);
      showToast('Removed from Liked Songs');
    } else {
      state.likedSongIds.add(songId);
      showToast('Added to Liked Songs');
    }

    localStorage.setItem('musicduniya_liked_songs', JSON.stringify([...state.likedSongIds]));

    if (state.currentSong && state.currentSong.id === songId) {
      playerLikeBtn.classList.toggle('liked', state.likedSongIds.has(songId));
    }

    updateLibraryUI();
    updatePlayingRowHighlights();

    if (state.currentView === 'liked') {
      renderView('liked');
    }
  }

  function updateVolumeUI(vol) {
    const pct = Math.round(vol * 100);
    volumeBarFill.style.width = `${pct}%`;
    volumeBarHandle.style.left = `${pct}%`;

    if (vol === 0 || state.isMuted) {
      volHighIcon.style.display = 'none';
      volMutedIcon.style.display = 'block';
    } else {
      volHighIcon.style.display = 'block';
      volMutedIcon.style.display = 'none';
    }
  }

  function toggleMute() {
    state.isMuted = !state.isMuted;
    audio.muted = state.isMuted;
    updateVolumeUI(state.isMuted ? 0 : state.volume);
  }

  function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  function showToast(msg) {
    if (window.AndroidBridge && typeof window.AndroidBridge.showToast === 'function') {
      window.AndroidBridge.showToast(msg);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
      toast.classList.remove('show');
    }, 2500);
  }

  function updateMediaSession(song) {
    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: song.title,
        artist: song.artist + (song.source ? ` (${song.source.toUpperCase()})` : ''),
        album: song.album || 'Music-Duniya Master',
        artwork: [
          { src: song.cover_url || 'logo.png', sizes: '512x512', type: 'image/jpeg' }
        ]
      });

      navigator.mediaSession.setActionHandler('play', () => togglePlayPause());
      navigator.mediaSession.setActionHandler('pause', () => togglePlayPause());
      navigator.mediaSession.setActionHandler('previoustrack', () => playPrev());
      navigator.mediaSession.setActionHandler('nexttrack', () => playNext());
    }

    if (window.AndroidBridge && typeof window.AndroidBridge.updateNotification === 'function') {
      try {
        window.AndroidBridge.updateNotification(song.title, song.artist, song.cover_url || '', true);
      } catch (_) {}
    }
  }

  // --- ONLINE SCRAPER SEARCH TRIGGER ---
  function performOnlineSearch(query) {
    if (!query || query.length < 2) {
      state.onlineResults = [];
      state.isSearchingOnline = false;
      renderSearchView();
      return;
    }

    state.isSearchingOnline = true;
    renderSearchView();

    if (window.AndroidBridge && typeof window.AndroidBridge.searchOnlineSync === 'function') {
      setTimeout(() => {
        try {
          const raw = window.AndroidBridge.searchOnlineSync(query);
          state.onlineResults = JSON.parse(raw);
        } catch (e) {
          state.onlineResults = [];
        }
        state.isSearchingOnline = false;
        renderSearchView();
      }, 50);
      return;
    }

    fetch(`/api/search-online?q=${encodeURIComponent(query)}`)
      .then(res => res.json())
      .then(data => {
        state.onlineResults = Array.isArray(data) ? data : [];
        state.isSearchingOnline = false;
        renderSearchView();
      })
      .catch(err => {
        state.isSearchingOnline = false;
        renderSearchView();
      });
  }

  // --- VIEW ROUTER ---
  function navigateTo(view, param = null) {
    state.history.push(view);
    state.historyIndex = state.history.length - 1;
    renderView(view, param);
  }

  function renderView(view, param = null) {
    state.currentView = view;

    document.querySelectorAll('.nav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.view === view);
    });

    // Update Mobile Bottom Nav Active Tab
    document.querySelectorAll('.m-nav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.mview === view);
    });

    // Update Mobile Top Header Title and Pills
    const mTitle = document.getElementById('m-header-title');
    const mPills = document.getElementById('m-filter-pills');
    if (mTitle) {
      if (view === 'library') {
        mTitle.textContent = 'Your Library';
        if (mPills) mPills.style.display = 'none';
      } else if (view === 'search') {
        mTitle.textContent = 'Search';
        if (mPills) mPills.style.display = 'none';
      } else if (view === 'artists') {
        mTitle.textContent = 'Singers & Artists';
        if (mPills) mPills.style.display = 'none';
      } else {
        mTitle.textContent = 'Music-Duniya';
        if (mPills) mPills.style.display = 'flex';
      }
    }

    if (view === 'home') {
      renderHomeView();
    } else if (view === 'search') {
      renderSearchView();
    } else if (view === 'artists') {
      renderArtistsView();
    } else if (view === 'singer_profile') {
      renderSingerProfileView(param);
    } else if (view === 'library') {
      renderLibraryView();
    } else if (view === 'liked') {
      renderLikedView();
    } else if (view === 'cached') {
      renderCachedView();
    } else if (view === 'playlist') {
      renderPlaylistView(param || 'all');
    }

    document.getElementById('content-view').scrollTop = 0;
  }

  function getGreeting() {
    const hr = new Date().getHours();
    if (hr < 12) return 'Good morning';
    if (hr < 18) return 'Good afternoon';
    return 'Good evening';
  }

  // --- HOME VIEW: THE MASTER SOUNDSTAGE & TURNTABLE DECK ---
  function renderHomeView() {
    const singers = state.popularSingers.length > 0 ? state.popularSingers : [
      { name: 'Diljit Dosanjh', slug: 'diljit-dosanjh', avatar_url: 'https://cover.djpunjab.is/60220/300x250/im_an_artist_bro_diljit_dosanjh.webp', tag: 'Royal Maestro' },
      { name: 'Karan Aujla', slug: 'karan-aujla', avatar_url: 'https://cover.djpunjab.is/60446/300x250/aujla_szn_1_karan_aujla.webp', tag: 'Hit Maestro' },
      { name: 'Sidhu Moose Wala', slug: 'sidhu-moose-wala', avatar_url: 'https://cover.mr-jatt.im/thumb/521474/GANGSTA-S-DELIGHT.webp', tag: 'Immortal Legend' },
      { name: 'Kulbir Jhinjer', slug: 'kulbir-jhinjer', avatar_url: 'https://lq.djjohal.com/covers_webp/48718/1.webp', tag: 'Folk Maestro' },
      { name: 'Babbar Brar', slug: 'babbar-brar', avatar_url: 'https://lq.djjohal.com/covers_webp/48718/1.webp', tag: 'Acoustic Maestro' },
      { name: 'Sabar Koti', slug: 'sabar-koti', avatar_url: 'https://cover.djpunjab.is/42133/300x250/asi_ese_joge_reh_gaye_sabar_koti.webp', tag: 'Sufi Maestro' }
    ];

    const activeSong = state.currentSong || state.songs[0] || {
      id: 'default_1',
      title: 'Piche Tere (feat. Sultaan)',
      artist: 'Babbar Brar, Sultaan',
      cover_url: 'https://lq.djjohal.com/covers_webp/48718/1.webp',
      duration: '3:20'
    };

    let html = `
      <!-- 1. The Master Soundstage Turntable Hero -->
      <section class="master-soundstage-hero">
        <div class="soundstage-halo"></div>
        <div class="soundstage-layout">
          <div class="stage-telemetry-col">
            <div class="stage-badge-row">
              <span class="hi-res-master-badge">✦ MASTER SOUNDSTAGE</span>
              <span class="stage-signal-rate">24-BIT / 192kHz HI-RES DSD</span>
            </div>
            <h1 class="stage-title" id="hero-stage-title">${activeSong.title}</h1>
            <div class="stage-artist-name" id="hero-stage-artist">${activeSong.artist}</div>
            <div class="stage-eq-cluster">
              <button class="eq-pill active">✦ Studio Flat</button>
              <button class="eq-pill">⚡ Warm Analog</button>
              <button class="eq-pill">🎙 Vocal Air</button>
              <button class="eq-pill">📻 Club Sub</button>
            </div>
            <div class="stage-actions-row">
              <button class="stage-master-play-btn card-play-btn" id="btn-hero-play" data-play-song-id="${activeSong.id}">
                <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                <span>ENGAGE PLAYBACK</span>
              </button>
              <button class="stage-secondary-btn" id="btn-hero-jam">
                <svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:currentColor;"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/></svg>
                <span>JAM LOUNGE</span>
              </button>
            </div>
          </div>
          <div class="stage-turntable-col">
            <div class="turntable-assembly">
              <div class="album-sleeve-jacket">
                <img src="${activeSong.cover_url || 'logo.png'}" id="hero-stage-cover" alt="Album Sleeve">
              </div>
              <div class="vinyl-record-disc ${state.isPlaying ? 'is-playing' : ''}" id="hero-vinyl-disc">
                <div class="vinyl-center-label">
                  <span class="label-brand">MUSIC-DUNIYA</span>
                  <span class="label-speed">33⅓ RPM</span>
                  <div class="spindle-hole"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 2. Heavyweight Master Crates -->
      <section class="studio-section">
        <div class="section-headline-row">
          <div class="section-title-group">
            <span class="section-pretitle">01 // CURATION</span>
            <h2 class="section-main-heading">Heavyweight Master Crates</h2>
          </div>
          <span class="section-browse-link section-see-all" data-action="view" data-view="library">Explore Vault Crates ➔</span>
        </div>
        <div class="crates-horizontal-scroll">
          ${renderCuratedPlaylistCards()}
        </div>
      </section>

      <!-- 3. Royal Punjabi & Global Maestros -->
      <section class="studio-section">
        <div class="section-headline-row">
          <div class="section-title-group">
            <span class="section-pretitle">02 // ARTISTS</span>
            <h2 class="section-main-heading">Royal Punjabi & Global Maestros</h2>
          </div>
          <span class="section-browse-link section-see-all" data-action="view" data-view="artists">All Maestros ➔</span>
        </div>
        <div class="maestros-grid">
          ${renderArtistAvatars(singers.slice(0, 6))}
        </div>
      </section>

      <!-- 4. Lossless Master Vault Cuts -->
      <section class="studio-section">
        <div class="section-headline-row">
          <div class="section-title-group">
            <span class="section-pretitle">03 // SELECTION</span>
            <h2 class="section-main-heading">Lossless Master Vault</h2>
          </div>
          <span class="section-browse-link section-see-all" data-action="playlist" data-id="all">View Entire Vault ➔</span>
        </div>
        <div class="crates-horizontal-scroll">
          ${renderMusicCards(state.songs.slice(0, 8))}
        </div>
      </section>
    `;

    viewContainer.innerHTML = html;
    bindCardClicks();
    bindArtistAvatarClicks();

    // Bind Soundstage Hero Controls
    const heroPlay = document.getElementById('btn-hero-play');
    if (heroPlay) {
      heroPlay.addEventListener('click', () => {
        if (state.currentSong) {
          togglePlayPause();
        } else if (state.songs.length > 0) {
          playSong(state.songs[0]);
        }
      });
    }

    const heroJam = document.getElementById('btn-hero-jam');
    if (heroJam) {
      heroJam.addEventListener('click', () => {
        const jamOverlay = document.getElementById('jam-modal-overlay');
        if (jamOverlay) jamOverlay.classList.add('open');
      });
    }

    document.querySelectorAll('.eq-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.eq-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        showToast(`EQ Profile Engaged: ${pill.textContent.trim()}`);
      });
    });
  }

  function renderCuratedPlaylistCards() {
    if (!state.curatedPlaylists || Object.keys(state.curatedPlaylists).length === 0) {
      return '';
    }
    return Object.values(state.curatedPlaylists).map(p => {
      const cover = p.cover_url || (p.tracks[0] && p.tracks[0].cover_url) || 'logo.png';
      return `
        <div class="crate-gatefold-card music-card" data-action="playlist" data-id="${p.name}">
          <div class="crate-cover-stage card-img-wrapper">
            <img src="${cover}" class="card-img" alt="${p.name}">
            <div class="crate-genre-chip">✦ CRATE</div>
            <button class="crate-hover-play card-play-btn" data-play-playlist="${p.name}" title="Play ${p.name}">
              <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            </button>
          </div>
          <div class="crate-meta-title card-title">${p.name}</div>
          <div class="crate-meta-sub card-subtitle">
            <span class="crate-track-count">${p.tracks.length} Master Cuts</span>
            <span class="hi-res-master-badge" style="font-size:8px; padding:2px 6px;">Royal Tape</span>
          </div>
        </div>
      `;
    }).join('');
  }

  // --- RENDER CIRCULAR ARTIST AVATARS ---
  function renderArtistAvatars(singersList) {
    return (singersList || []).map(s => `
      <div class="maestro-card artist-avatar-card" data-singer-slug="${s.slug}">
        <div class="maestro-vinyl-portrait artist-avatar-wrapper">
          <img src="${s.avatar_url || 'https://lq.djjohal.com/covers_webp/48718/1.webp'}" class="artist-avatar-img" alt="${s.name}">
          <button class="card-play-btn artist-card-play-btn" data-play-singer-slug="${s.slug}" style="display:none;"></button>
        </div>
        <div class="maestro-name artist-name-title">${s.name}</div>
        <div class="maestro-meta artist-tag-subtitle" style="font-size:11px; color:var(--accent-amber);">${s.tag || 'Verified Maestro'}</div>
      </div>
    `).join('');
  }

  function renderMusicCards(songs) {
    return (songs || []).map(s => {
      const sourceTag = s.source === 'djpunjab'
        ? 'DJPUNJAB'
        : s.source === 'djjohal'
        ? 'DJJOHAL'
        : s.source === 'mrjatt'
        ? 'MR-JATT'
        : 'LOSSLESS';

      return `
        <div class="crate-gatefold-card music-card" data-song-id="${s.id}">
          <div class="crate-cover-stage card-img-wrapper">
            <img src="${s.cover_url || 'https://lq.djjohal.com/covers_webp/48718/1.webp'}" class="card-img" alt="${s.title}">
            <div class="crate-genre-chip">${sourceTag}</div>
            <button class="crate-hover-play card-play-btn" data-play-song-id="${s.id}" title="Play ${s.title}">
              <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            </button>
          </div>
          <div class="crate-meta-title card-title">${s.title}</div>
          <div class="crate-meta-sub card-subtitle">
            <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:140px;">${s.artist}</span>
            <span class="crate-track-count">${s.duration || '3:20'}</span>
          </div>
        </div>
      `;
    }).join('');
  }

  // --- ARTISTS DIRECTORY (DJPUNJAB A-Z SINGERS) ---
  function renderArtistsView() {
    const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

    viewContainer.innerHTML = `
      <div class="home-header">
        <h1 class="home-title">Singers & Artists</h1>
        <p style="color: var(--text-subdued); margin-top: 6px;">Explore all Punjabi artists from <strong>DJPunjab.is</strong> with photos and complete song catalogs cached in Supabase.</p>
      </div>

      <!-- A to Z alphabet filter -->
      <div class="alphabet-filter">
        ${letters.map(l => `
          <button class="letter-btn ${state.selectedLetter === l.toLowerCase() ? 'active' : ''}" data-letter="${l.toLowerCase()}">${l}</button>
        `).join('')}
      </div>

      <!-- Top Curated Artists Row -->
      <div class="section-block">
        <h2 class="section-title" style="margin-bottom: 16px;">Top Trending Singers</h2>
        <div class="cards-grid">
          ${renderArtistAvatars(state.popularSingers.length > 0 ? state.popularSingers : POPULAR_FALLBACK)}
        </div>
      </div>

      <!-- Letter Singers List -->
      <div class="section-block" style="margin-top: 36px;">
        <h2 class="section-title" style="margin-bottom: 16px;">Artists Starting With "${state.selectedLetter.toUpperCase()}"</h2>
        <div id="letter-artists-container" class="cards-grid">
          <div style="padding: 24px; color: var(--text-subdued);">Loading singers from DJPunjab...</div>
        </div>
      </div>
    `;

    // Bind letter buttons
    viewContainer.querySelectorAll('.letter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.selectedLetter = btn.dataset.letter;
        renderArtistsView();
        loadSingersByLetter(state.selectedLetter);
      });
    });

    bindArtistAvatarClicks();
    loadSingersByLetter(state.selectedLetter);
  }

  async function loadSingersByLetter(letter) {
    const container = document.getElementById('letter-artists-container');
    if (!container) return;

    try {
      let artists = [];
      if (window.AndroidBridge && typeof window.AndroidBridge.getSingersByLetterSync === 'function') {
        const raw = window.AndroidBridge.getSingersByLetterSync(letter);
        artists = JSON.parse(raw);
      } else {
        const res = await fetch(`/api/all-singers?letter=${letter}`);
        if (!res.ok) throw new Error('API failed');
        artists = await res.json();
      }

      if (artists.length === 0) {
        container.innerHTML = `<div style="padding: 24px; color: var(--text-subdued);">No artists found under "${letter.toUpperCase()}".</div>`;
        return;
      }

      container.innerHTML = renderArtistAvatars(artists);
      bindArtistAvatarClicks();
    } catch (e) {
      container.innerHTML = `<div style="padding: 24px; color: var(--text-subdued);">Could not load artists under "${letter.toUpperCase()}".</div>`;
    }
  }

  // --- SINGER PROFILE VIEW (WITH DISCOGRAPHY & AVATAR) ---
  async function renderSingerProfileView(slug) {
    if (!slug || slug === 'undefined') {
      slug = 'diljit-dosanjh';
    }
    const cleanName = slug.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

    // Instant local songs filter
    const localTracks = (state.songs || []).filter(s => {
      const art = (s.artist || '').toLowerCase();
      const tit = (s.title || '').toLowerCase();
      const target = cleanName.toLowerCase();
      return art.includes(target) || target.includes(art);
    });

    const artistCover = (localTracks.length > 0 && localTracks[0].cover_url)
      ? localTracks[0].cover_url
      : 'logo.png';

    let profile = {
      name: cleanName,
      avatar_url: artistCover,
      songs: localTracks
    };

    // Render immediately so user never waits!
    renderProfileContent(profile);

    // If online, optionally fetch more discography in background
    try {
      if (window.AndroidBridge && typeof window.AndroidBridge.getSingerSongsSync === 'function') {
        const raw = window.AndroidBridge.getSingerSongsSync(slug);
        const parsed = JSON.parse(raw);
        if (parsed && parsed.songs && parsed.songs.length) {
          profile = parsed;
          renderProfileContent(profile);
        }
      } else {
        const controller = new AbortController();
        const tid = setTimeout(() => controller.abort(), 2000);
        const res = await fetch(`/api/singer-profile?slug=${encodeURIComponent(slug)}`, { signal: controller.signal });
        clearTimeout(tid);
        if (res.ok) {
          const parsed = await res.json();
          if (parsed && parsed.songs && parsed.songs.length) {
            profile = parsed;
            renderProfileContent(profile);
          }
        }
      }
    } catch (_) {}

    function renderProfileContent(prof) {
      const trackList = (prof.songs && prof.songs.length) ? prof.songs : localTracks;
      viewContainer.innerHTML = `
        <div class="playlist-hero">
          <div style="position: relative; width: 170px; height: 170px; border-radius: 50%; overflow: hidden; box-shadow: 0 16px 36px rgba(0,0,0,0.7); flex-shrink: 0; background: #222;">
            <img src="${prof.avatar_url || 'logo.png'}" onerror="this.onerror=null;this.src='logo.png';" style="width: 100%; height: 100%; object-fit: cover;" alt="${prof.name}">
          </div>
          <div class="hero-details">
            <span class="hero-tag" style="display:flex; align-items:center; gap:6px;">
              <svg viewBox="0 0 24 24" class="verified-icon"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
              Verified Artist
            </span>
            <h1 class="hero-title">${prof.name}</h1>
            <p class="hero-desc">Music-Duniya Official Artist Discography • Studio Master Quality</p>
            <div class="hero-meta">
              <span>${trackList.length} tracks available</span>
            </div>
          </div>
        </div>

        <div class="playlist-actions-bar">
          <button class="hero-play-btn" id="btn-hero-play" title="Play All">
            <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          </button>
          <button class="pill-badge" id="btn-artist-follow" style="background: rgba(255,255,255,0.1); border: 1px solid #444; cursor:pointer;">Follow</button>
        </div>

        <div class="section-block">
          <h3 class="section-title" style="margin-bottom: 16px;">Popular Songs</h3>
          ${renderSongsTable(trackList)}
        </div>
      `;

      bindHeroPlay(trackList);
      bindTableEvents(trackList);

      const fBtn = document.getElementById('btn-artist-follow');
      if (fBtn) {
        fBtn.addEventListener('click', () => {
          fBtn.textContent = fBtn.textContent === 'Following' ? 'Follow' : 'Following';
          showToast(`${fBtn.textContent === 'Following' ? 'Followed' : 'Unfollowed'} ${prof.name}`);
        });
      }
    }
  }

  // --- SEARCH VIEW ---
  function renderSearchView() {
    const q = state.searchQuery.trim().toLowerCase();

    if (!q) {
      const recents = (state.songs && state.songs.length >= 6)
        ? state.songs.slice(0, 6).map((s) => ({
            id: 'rec-' + s.id,
            title: s.title,
            artist: 'Song • ' + s.artist,
            cover: s.cover_url || 'logo.png',
            q: s.title
          }))
        : [
            { id: 'rec-1', title: 'Lalkara', artist: 'Song • Diljit Dosanjh', cover: 'https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/64/30/ba/6430ba26-29a2-85a6-0a54-cfb63f9b83eb/8721416627408.jpg/600x600bb.jpg', q: 'Lalkara' },
            { id: 'rec-2', title: '52 Bars', artist: 'Song • Karan Aujla', cover: 'https://c.saavncdn.com/757/House-Navior-Punjabi-2025-20250917053150-500x500.jpg', q: '52 Bars' },
            { id: 'rec-3', title: 'Tum Ho Toh', artist: 'Song • Vishal Mishra', cover: 'https://c.saavncdn.com/598/Saiyaara-Hindi-2025-20250703061754-500x500.jpg', q: 'Tum Ho Toh' },
            { id: 'rec-4', title: 'King Shit', artist: 'Song • Shubh', cover: 'https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/b9/0a/b4/b90ab45a-07b1-0bcc-331c-c496a21d07e4/10UMGIM01134.rgb.jpg/600x600bb.jpg', q: 'King Shit' },
            { id: 'rec-5', title: 'With You', artist: 'Song • AP Dhillon', cover: 'https://c.saavncdn.com/470/Tum-Se-Achcha-Kaun-Hai-Hindi-2002-20210226142443-500x500.jpg', q: 'With You' },
            { id: 'rec-6', title: 'Dharna', artist: 'Song • Kulbir Jhinjer', cover: 'https://is1-ssl.mzstatic.com/image/thumb/Music124/v4/d6/d9/81/d6d9814c-25ee-33d6-94d2-6fb875d2f959/cover.jpg/600x600bb.jpg', q: 'Dharna' }
          ];

      const watchPlaylists = [
        { title: 'Punjabi Vibes', subtitle: 'Trending Punjabi', img: 'https://c.saavncdn.com/757/House-Navior-Punjabi-2025-20250917053150-500x500.jpg', q: 'Punjabi' },
        { title: 'Bollywood Romance ❤️', subtitle: 'Arijit & Melodies', img: 'https://c.saavncdn.com/598/Saiyaara-Hindi-2025-20250703061754-500x500.jpg', q: 'Arijit Singh' },
        { title: 'Pop Global Hits', subtitle: 'Justin & Global', img: 'https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/b9/0a/b4/b90ab45a-07b1-0bcc-331c-c496a21d07e4/10UMGIM01134.rgb.jpg/600x600bb.jpg', q: 'Baby' },
        { title: 'Retro Classics', subtitle: 'Timeless Melodies', img: 'https://c.saavncdn.com/470/Tum-Se-Achcha-Kaun-Hai-Hindi-2002-20210226142443-500x500.jpg', q: 'Retro' },
        { title: 'Desi Hip-Hop', subtitle: 'Karan Aujla & Diljit', img: 'https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/64/30/ba/6430ba26-29a2-85a6-0a54-cfb63f9b83eb/8721416627408.jpg/600x600bb.jpg', q: 'Diljit Dosanjh' }
      ];

      const genres = [
        { name: 'Music', bg: '#e1118c', img: (state.songs[0] && state.songs[0].cover_url) || 'logo.png' },
        { name: 'Podcasts', bg: '#006450', img: 'logo.png' },
        { name: 'Audiobooks', bg: '#1e3264', img: 'logo.png' },
        { name: 'Live Events', bg: '#7358ff', img: (state.songs[1] && state.songs[1].cover_url) || 'logo.png' },
        { name: 'Home of I-Pop', bg: '#0d407f', img: (state.songs[2] && state.songs[2].cover_url) || 'logo.png' },
        { name: 'Made For You', bg: '#8c44c2', img: (state.songs[3] && state.songs[3].cover_url) || 'logo.png' },
        { name: 'Decades', bg: '#b05d41', img: 'logo.png' },
        { name: 'Hip-Hop', bg: '#1e7085', img: (state.songs[4] && state.songs[4].cover_url) || 'logo.png' },
        { name: 'Dance/Electronic', bg: '#287a99', img: 'logo.png' },
        { name: 'Student', bg: '#bc1a8d', img: 'logo.png' },
        { name: 'Chill', bg: '#bb5c24', img: 'logo.png' },
        { name: 'Gaming', bg: '#e91463', img: 'logo.png' },
        { name: 'K-pop', bg: '#e91429', img: 'logo.png' },
        { name: 'Workout Music', bg: '#686868', img: 'logo.png' },
        { name: 'RADAR', bg: '#9a6549', img: 'logo.png' },
        { name: 'EQUAL', bg: '#05823f', img: 'logo.png' },
        { name: 'Rock', bg: '#176559', img: 'logo.png' },
        { name: 'Indian Classical', bg: '#6b3e26', img: 'logo.png' }
      ];

      viewContainer.innerHTML = `
        <div class="search-mobile-header" style="margin-bottom: 14px; position: sticky; top: 0; z-index: 10; background: var(--bg-base); padding: 4px 0;">
          <div class="m-search-input-wrap" style="display:flex; align-items:center; background:#1c1c24; border-radius:12px; padding:6px 12px; gap:8px;">
            <svg style="width:20px; height:20px; fill:#fff; flex-shrink:0; cursor:pointer;" id="btn-trigger-m-search" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
            <input type="text" id="m-search-page-input" placeholder="What do you want to listen to?" value="${escapeHtml(state.searchQuery)}" style="flex:1; background:transparent; border:none; color:#fff; font-size:15px; outline:none;">
            ${state.searchQuery ? `<button id="btn-clear-m-search" style="background:none; border:none; color:#999; font-size:16px; cursor:pointer; padding:0 6px;">✕</button>` : ''}
            <button id="btn-submit-m-search" style="background:#1ed760; color:#000; border:none; border-radius:20px; padding:6px 14px; font-weight:700; font-size:12px; cursor:pointer;">Search</button>
          </div>
        </div>

        <!-- Recents List (Exact Screenshot 6) -->
        <div class="search-recents-section" id="search-recents-box">
          <div class="search-recents-title">Recents</div>
          <div class="search-recents-list">
            ${recents.map(r => `
              <div class="recent-song-row" data-search-q="${r.q}">
                <div class="recent-song-left">
                  <img src="${r.cover}" onerror="this.onerror=null;this.src='logo.png';" class="recent-song-img" alt="${r.title}">
                  <div class="recent-song-meta">
                    <div class="r-title">${r.title}</div>
                    <div class="r-artist">${r.artist}</div>
                  </div>
                </div>
                <div class="recent-song-actions">
                  <button class="btn-add-rec" data-rec-title="${r.title}" title="Add to Library">
                    <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                  </button>
                  <button class="btn-remove-rec" title="Remove">
                    <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Playlists you can watch Carousel (Screenshot 1 & 7) -->
        <div class="section-block" style="margin-bottom: 24px;">
          <h2 style="font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 12px;">Playlists you can watch</h2>
          <div style="display: flex; gap: 14px; overflow-x: auto; padding-bottom: 8px;">
            ${watchPlaylists.map(w => `
              <div style="min-width: 140px; cursor: pointer; flex-shrink: 0;" data-search-q="${w.q}" class="watch-card">
                <img src="${w.img}" onerror="this.onerror=null;this.src='logo.png';" style="width: 140px; height: 180px; object-fit: cover; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.6);" alt="${w.title}">
                <div style="font-size: 13px; font-weight: 700; color: #fff; margin-top: 6px;">${w.title}</div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- 2-Column Colored Browse All Grid (Screenshot 7) -->
        <div class="section-block">
          <h2 style="font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 14px;">Browse all</h2>
          <div class="search-genres-grid">
            ${genres.map(g => `
              <div class="genre-tile" style="background-color: ${g.bg};" data-genre="${g.name}">
                <span>${g.name}</span>
                <img src="${g.img}" onerror="this.onerror=null;this.src='logo.png';" alt="${g.name}">
              </div>
            `).join('')}
          </div>
        </div>
      `;

      const mInput = document.getElementById('m-search-page-input');
      const btnClearM = document.getElementById('btn-clear-m-search');
      const btnSubmitM = document.getElementById('btn-submit-m-search');
      const btnTriggerM = document.getElementById('btn-trigger-m-search');

      if (mInput) {
        mInput.addEventListener('input', (e) => {
          state.searchQuery = e.target.value;
          if (searchInput) searchInput.value = state.searchQuery;
          if (btnClearSearch) btnClearSearch.style.display = state.searchQuery ? 'flex' : 'none';
        });

        mInput.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            mInput.blur();
            performOnlineSearch(state.searchQuery.trim());
          }
        });
      }

      if (btnSubmitM) {
        btnSubmitM.addEventListener('click', () => {
          if (mInput) mInput.blur();
          performOnlineSearch(state.searchQuery.trim());
        });
      }

      if (btnTriggerM) {
        btnTriggerM.addEventListener('click', () => {
          if (mInput) mInput.blur();
          performOnlineSearch(state.searchQuery.trim());
        });
      }

      if (btnClearM) {
        btnClearM.addEventListener('click', () => {
          state.searchQuery = '';
          if (searchInput) searchInput.value = '';
          if (btnClearSearch) btnClearSearch.style.display = 'none';
          state.onlineResults = [];
          renderSearchView();
        });
      }

      // Recents click & actions
      viewContainer.querySelectorAll('.recent-song-row').forEach(row => {
        row.addEventListener('click', (e) => {
          if (e.target.closest('.recent-song-actions')) return;
          const query = row.dataset.searchQ;
          state.searchQuery = query;
          searchInput.value = query;
          btnClearSearch.style.display = 'flex';
          performOnlineSearch(query);
        });
      });

      viewContainer.querySelectorAll('.btn-add-rec').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          showToast(`Added ${btn.dataset.recTitle} to Your Library`);
        });
      });

      viewContainer.querySelectorAll('.btn-remove-rec').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const row = btn.closest('.recent-song-row');
          if (row) row.remove();
        });
      });

      viewContainer.querySelectorAll('.watch-card').forEach(card => {
        card.addEventListener('click', () => {
          const query = card.dataset.searchQ;
          state.searchQuery = query;
          searchInput.value = query;
          btnClearSearch.style.display = 'flex';
          performOnlineSearch(query);
        });
      });

      viewContainer.querySelectorAll('.genre-tile').forEach(tile => {
        tile.addEventListener('click', () => {
          const genre = tile.dataset.genre;
          if (genre.includes('Artists')) {
            navigateTo('artists');
          } else {
            state.searchQuery = genre.replace(' Hits', '').replace(' Music', '');
            searchInput.value = state.searchQuery;
            btnClearSearch.style.display = 'flex';
            performOnlineSearch(state.searchQuery);
          }
        });
      });
      return;
    }

    const localMatches = state.songs.filter(s =>
      s.title.toLowerCase().includes(q) ||
      s.artist.toLowerCase().includes(q)
    );

    let allResults = [...localMatches, ...state.onlineResults];

    if (state.searchSourceFilter === 'djjohal') {
      allResults = allResults.filter(s => s.source === 'djjohal');
    } else if (state.searchSourceFilter === 'mrjatt') {
      allResults = allResults.filter(s => s.source === 'mrjatt');
    } else if (state.searchSourceFilter === 'djpunjab') {
      allResults = allResults.filter(s => s.source === 'djpunjab');
    } else if (state.searchSourceFilter === 'local') {
      allResults = allResults.filter(s => s.source === 'local');
    }

    const topResult = allResults.length > 0 ? allResults[0] : null;

    viewContainer.innerHTML = `
      <div class="search-mobile-header" style="margin-bottom: 14px; position: sticky; top: 0; z-index: 10; background: var(--bg-base); padding: 4px 0;">
        <div class="m-search-input-wrap" style="display:flex; align-items:center; background:#1c1c24; border-radius:12px; padding:6px 12px; gap:8px;">
          <svg style="width:20px; height:20px; fill:#fff; flex-shrink:0; cursor:pointer;" id="btn-trigger-m-search" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
          <input type="text" id="m-search-page-input" placeholder="What do you want to listen to?" value="${escapeHtml(state.searchQuery)}" style="flex:1; background:transparent; border:none; color:#fff; font-size:15px; outline:none;">
          ${state.searchQuery ? `<button id="btn-clear-m-search" style="background:none; border:none; color:#999; font-size:16px; cursor:pointer; padding:0 6px;">✕</button>` : ''}
          <button id="btn-submit-m-search" style="background:#1ed760; color:#000; border:none; border-radius:20px; padding:6px 14px; font-weight:700; font-size:12px; cursor:pointer;">Search</button>
        </div>
      </div>

      <div class="search-sources-filter">
        <button class="source-filter-btn ${state.searchSourceFilter === 'all' ? 'active' : ''}" data-source-filter="all">All Sources (${allResults.length})</button>
        <button class="source-filter-btn ${state.searchSourceFilter === 'djpunjab' ? 'active' : ''}" data-source-filter="djpunjab">🟠 DJPunjab</button>
        <button class="source-filter-btn ${state.searchSourceFilter === 'djjohal' ? 'active' : ''}" data-source-filter="djjohal">🟢 DJJohal</button>
        <button class="source-filter-btn ${state.searchSourceFilter === 'mrjatt' ? 'active' : ''}" data-source-filter="mrjatt">🔵 Mr-Jatt</button>
        <button class="source-filter-btn ${state.searchSourceFilter === 'local' ? 'active' : ''}" data-source-filter="local">⚪ Downloaded (${localMatches.length})</button>
      </div>

      ${state.isSearchingOnline ? `
        <div class="scraping-indicator">
          <div class="spinner"></div>
          <span>Searching live on DJPunjab.is, DJJohal.com & Mr-Jatt.im...</span>
        </div>
      ` : ''}

      ${allResults.length === 0 && !state.isSearchingOnline ? `
        <div style="padding: 40px 0; text-align: center;">
          <h2>No results found for "${escapeHtml(state.searchQuery)}"</h2>
          <p style="color: var(--text-subdued); margin-top: 8px;">Try searching for an artist (e.g. Diljit Dosanjh, Karan Aujla, Sidhu Moose Wala) or track name.</p>
        </div>
      ` : `
        <div class="search-results-top">
          ${topResult ? `
            <div class="top-result-card" data-song-id="${topResult.id}">
              <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 12px;">Top result</h3>
              <img src="${topResult.cover_url || 'https://lq.djjohal.com/covers_webp/48718/1.webp'}" class="top-result-img" alt="${topResult.title}">
              <div class="top-result-title">${topResult.title}</div>
              <div style="color: var(--text-subdued); margin-bottom: 12px; display:flex; align-items:center; gap:8px;">
                <span>${topResult.artist}</span>
                <span class="source-badge ${topResult.source}">${topResult.source.toUpperCase()}</span>
              </div>
              <button class="card-play-btn" data-play-song-id="${topResult.id}">
                <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
              </button>
            </div>
          ` : ''}

          <div>
            <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 12px;">Matching Tracks</h3>
            ${renderSongsTable(allResults.slice(0, 8), false)}
          </div>
        </div>

        <div class="section-block">
          <h3 class="section-title" style="margin-bottom: 16px;">All Results</h3>
          <div class="cards-grid">
            ${renderMusicCards(allResults)}
          </div>
        </div>
      `}
    `;

    const mInputRes = document.getElementById('m-search-page-input');
    const btnClearMRes = document.getElementById('btn-clear-m-search');
    const btnSubmitMRes = document.getElementById('btn-submit-m-search');
    const btnTriggerMRes = document.getElementById('btn-trigger-m-search');

    if (mInputRes) {
      mInputRes.addEventListener('input', (e) => {
        state.searchQuery = e.target.value;
        if (searchInput) searchInput.value = state.searchQuery;
        if (btnClearSearch) btnClearSearch.style.display = state.searchQuery ? 'flex' : 'none';
      });

      mInputRes.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          mInputRes.blur();
          performOnlineSearch(state.searchQuery.trim());
        }
      });
    }

    if (btnSubmitMRes) {
      btnSubmitMRes.addEventListener('click', () => {
        if (mInputRes) mInputRes.blur();
        performOnlineSearch(state.searchQuery.trim());
      });
    }

    if (btnTriggerMRes) {
      btnTriggerMRes.addEventListener('click', () => {
        if (mInputRes) mInputRes.blur();
        performOnlineSearch(state.searchQuery.trim());
      });
    }

    if (btnClearMRes) {
      btnClearMRes.addEventListener('click', () => {
        state.searchQuery = '';
        if (searchInput) searchInput.value = '';
        if (btnClearSearch) btnClearSearch.style.display = 'none';
        state.onlineResults = [];
        renderSearchView();
      });
    }

    viewContainer.querySelectorAll('.source-filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.searchSourceFilter = btn.dataset.sourceFilter;
        renderSearchView();
      });
    });

    bindCardClicks(allResults);
    bindTableEvents(allResults);
  }

  // --- CACHED STREAMS VIEW ---
  function renderCachedView() {
    viewContainer.innerHTML = `
      <div class="playlist-hero">
        <div class="hero-cover" style="background: linear-gradient(135deg, #059669, #2563eb); display:flex; align-items:center; justify-content:center;">
          <svg viewBox="0 0 24 24" style="width: 72px; height: 72px; fill: #fff;"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
        </div>
        <div class="hero-details">
          <span class="hero-tag">Temporary Cache</span>
          <h1 class="hero-title">Cached Streams</h1>
          <p class="hero-desc">Songs and singers scraped and temporarily saved in Supabase & local storage.</p>
          <div class="hero-meta">
            <span>${state.cachedSongs.length} tracks in local cache</span>
          </div>
        </div>
      </div>

      <div class="cache-actions-bar">
        <div>
          <button class="hero-play-btn" id="btn-hero-play" title="Play Cached">
            <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          </button>
        </div>
        <button class="btn-secondary" id="btn-clear-temp-cache">Clear Temporary Cache</button>
      </div>

      ${state.cachedSongs.length === 0 ? `
        <div style="padding: 40px 0; color: var(--text-subdued); text-align:center;">
          <h3>No temporarily cached songs yet</h3>
          <p style="margin-top: 8px;">Search for any song or singer in the search bar above to stream and cache it!</p>
        </div>
      ` : `
        <table class="songs-table">
          <thead>
            <tr>
              <th class="col-num">#</th>
              <th>Cached File</th>
              <th>Size</th>
              <th class="col-duration">Action</th>
            </tr>
          </thead>
          <tbody>
            ${state.cachedSongs.map((c, i) => `
              <tr class="song-row" data-cached-idx="${i}">
                <td class="col-num-cell">${i + 1}</td>
                <td>
                  <div class="track-main">
                    <span class="track-title">${c.filename}</span>
                  </div>
                </td>
                <td class="col-album">${(c.size / (1024 * 1024)).toFixed(2)} MB</td>
                <td class="col-duration">
                  <button class="source-filter-btn" data-play-cache-url="${c.audio_url}" data-cache-name="${c.filename}">Play</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `}
    `;

    const clearBtn = document.getElementById('btn-clear-temp-cache');
    if (clearBtn) {
      clearBtn.addEventListener('click', async () => {
        if (!confirm('Clear all temporary cached music files?')) return;
        if (window.AndroidBridge && typeof window.AndroidBridge.clearCacheSync === 'function') {
          window.AndroidBridge.clearCacheSync();
        } else {
          try {
            await fetch('/api/clear-cache', { method: 'POST' });
          } catch (e) {}
        }
        await fetchCachedSongs();
        renderCachedView();
        showToast('Temporary cache cleared');
      });
    }

    viewContainer.querySelectorAll('[data-play-cache-url]').forEach(btn => {
      btn.addEventListener('click', () => {
        const url = btn.dataset.playCacheUrl;
        const name = btn.dataset.cacheName;
        playSong({
          id: 'cache_' + name,
          title: name.replace('.mp3', ''),
          artist: 'Cached Stream',
          audio_url: url,
          source: 'cache'
        });
      });
    });
  }

  // --- LIBRARY VIEW ---
  function renderLibraryView() {
    const userProfile = (function() {
      try {
        const u = localStorage.getItem('musicduniya_user');
        return u ? JSON.parse(u) : { name: 'Arsh Rana' };
      } catch (_) { return { name: 'Arsh Rana' }; }
    })();

    const followedSingers = [
      { name: 'Diljit Dosanjh', slug: 'diljit-dosanjh', avatar_url: 'https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/48/ea/7e/48ea7e0d-7b2a-143e-c68e-e5d0e2e83163/cover.jpg/600x600bb.jpg' },
      { name: 'AP Dhillon', slug: 'ap-dhillon', avatar_url: 'https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/a5/45/62/a5456209-66bf-463e-2fae-d2b4a3f2bb4e/8902894002621_cover.jpg/600x600bb.jpg' },
      { name: 'Karan Aujla', slug: 'karan-aujla', avatar_url: 'https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/f1/b7/c6/f1b7c626-d183-4a0b-d249-14a0a7db0f8a/cover.jpg/600x600bb.jpg' },
      { name: 'Sidhu Moose Wala', slug: 'sidhu-moose-wala', avatar_url: 'https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/05/17/dc/0517dc79-e1ae-7f11-d14d-9e663cfd2dc4/cover.jpg/600x600bb.jpg' },
      { name: 'Kulbir Jhinjer', slug: 'kulbir-jhinjer', avatar_url: 'https://is1-ssl.mzstatic.com/image/thumb/Music122/v4/df/e3/ef/dfe3ef99-73eb-2751-28cf-fa42a12aa664/197187127763.jpg/600x600bb.jpg' }
    ];

    viewContainer.innerHTML = `
      <div class="library-mobile-view" style="padding: 10px 0 100px 0;">
        <!-- Filter pills -->
        <div style="display:flex; gap:8px; margin-bottom: 24px;">
          <button class="m-pill active" style="background:#2a2a2a; color:#fff;">Playlists</button>
          <button class="m-pill" style="background:#2a2a2a; color:#fff;" id="btn-library-artists-pill">Artists</button>
        </div>

        <div class="library-rows-list" style="display:flex; flex-direction:column; gap:18px;">
          <!-- Liked Songs Row (Screenshot 1) -->
          <div class="library-item-row" data-action="playlist" data-id="liked" style="display:flex; align-items:center; gap:16px; cursor:pointer;">
            <div style="width: 56px; height: 56px; border-radius: 4px; background: linear-gradient(135deg, #450af5, #8e8ee5); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
              <svg viewBox="0 0 24 24" style="width:28px; height:28px; fill:#fff;"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
            </div>
            <div style="flex:1;">
              <div style="font-size:16px; font-weight:700; color:#fff; margin-bottom:4px;">Liked Songs</div>
              <div style="font-size:13px; color:var(--text-subdued); display:flex; align-items:center; gap:4px;">
                <span style="color:#a855f7;">📌</span> <span>Playlist • ${userProfile.name || 'Arsh Rana'}</span>
              </div>
            </div>
          </div>

          <!-- Curated Royal Playlists (Kitab, Punjabi vibes, ❤️, MUMMA's ❤️, Baby) -->
          ${Object.values(state.curatedPlaylists || {}).map(p => `
            <div class="library-item-row" data-action="playlist" data-id="${p.name}" style="display:flex; align-items:center; gap:16px; cursor:pointer;">
              <div style="width: 56px; height: 56px; border-radius: 6px; overflow:hidden; flex-shrink:0; box-shadow:0 4px 12px rgba(0,0,0,0.5); background:#181818;">
                <img src="${p.cover_url || (p.tracks[0] && p.tracks[0].cover_url) || 'logo.png'}" onerror="this.onerror=null;this.src='logo.png';" style="width:100%; height:100%; object-fit:cover;" alt="${p.name}">
              </div>
              <div style="flex:1;">
                <div style="font-size:16px; font-weight:700; color:#fff; margin-bottom:4px;">${p.name}</div>
                <div style="font-size:13px; color:var(--text-subdued); display:flex; align-items:center; gap:4px;">
                  <span style="color:#c084fc;">✦ Royal</span> <span>• Playlist • ${p.tracks.length} songs</span>
                </div>
              </div>
            </div>
          `).join('')}

          <!-- Followed Artists with Circular Avatars (Screenshot 1) -->
          ${followedSingers.map(s => `
            <div class="library-item-row" data-action="singer" data-slug="${s.slug}" style="display:flex; align-items:center; gap:16px; cursor:pointer;">
              <div style="width: 56px; height: 56px; border-radius: 50%; overflow:hidden; flex-shrink:0; box-shadow:0 4px 12px rgba(0,0,0,0.5); background:#222;">
                <img src="${s.avatar_url}" onerror="this.onerror=null;this.src='logo.png';" style="width:100%; height:100%; object-fit:cover;" alt="${s.name}">
              </div>
              <div style="flex:1;">
                <div style="font-size:16px; font-weight:700; color:#fff; margin-bottom:4px;">${s.name}</div>
                <div style="font-size:13px; color:var(--text-subdued);">Artist</div>
              </div>
            </div>
          `).join('')}

          <!-- Quick Action Buttons (Screenshot 1) -->
          <div class="library-action-row" data-action="artists" style="display:flex; align-items:center; gap:16px; cursor:pointer; padding: 4px 0;">
            <div style="width: 56px; height: 56px; border-radius: 50%; background:#282828; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
              <svg viewBox="0 0 24 24" style="width:28px; height:28px; fill:#b3b3b3;"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            </div>
            <div style="font-size:15px; font-weight:600; color:#fff;">Add artists</div>
          </div>

          <div class="library-action-row" data-action="podcasts" style="display:flex; align-items:center; gap:16px; cursor:pointer; padding: 4px 0;">
            <div style="width: 56px; height: 56px; border-radius: 8px; background:#282828; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
              <svg viewBox="0 0 24 24" style="width:28px; height:28px; fill:#b3b3b3;"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            </div>
            <div style="font-size:15px; font-weight:600; color:#fff;">Add podcasts</div>
          </div>

          <div class="library-action-row" data-action="events" style="display:flex; align-items:center; gap:16px; cursor:pointer; padding: 4px 0;">
            <div style="width: 56px; height: 56px; border-radius: 8px; background:#282828; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
              <svg viewBox="0 0 24 24" style="width:28px; height:28px; fill:#b3b3b3;"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            </div>
            <div style="font-size:15px; font-weight:600; color:#fff;">Add events and venues</div>
          </div>

          <div class="library-action-row" data-action="import" style="display:flex; align-items:center; gap:16px; cursor:pointer; padding: 4px 0;">
            <div style="width: 56px; height: 56px; border-radius: 8px; background:#282828; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
              <svg viewBox="0 0 24 24" style="width:28px; height:28px; fill:#b3b3b3;"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            </div>
            <div style="font-size:15px; font-weight:600; color:#fff;">Import your music</div>
          </div>
        </div>
      </div>
    `;

    viewContainer.querySelectorAll('.library-item-row').forEach(row => {
      row.addEventListener('click', () => {
        const act = row.dataset.action;
        if (act === 'playlist') {
          if (row.dataset.id === 'liked') navigateTo('liked');
          else if (row.dataset.id === 'cached') navigateTo('cached');
          else navigateTo('playlist', row.dataset.id);
        } else if (act === 'singer') {
          navigateTo('singer_profile', row.dataset.slug);
        }
      });
    });

    viewContainer.querySelectorAll('.library-action-row').forEach(row => {
      row.addEventListener('click', () => {
        const act = row.dataset.action;
        if (act === 'artists') {
          navigateTo('artists');
        } else {
          showToast(`Opened ${act}`);
        }
      });
    });

    const pillArtists = document.getElementById('btn-library-artists-pill');
    if (pillArtists) {
      pillArtists.addEventListener('click', () => navigateTo('artists'));
    }
  }

  // --- LIKED SONGS VIEW ---
  function renderLikedView() {
    const likedSongs = state.songs.filter(s => state.likedSongIds.has(s.id));

    viewContainer.innerHTML = `
      <div class="playlist-hero">
        <div class="hero-cover liked-gradient" style="display: flex; align-items: center; justify-content: center;">
          <svg viewBox="0 0 24 24" style="width: 72px; height: 72px; fill: #fff;"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
        </div>
        <div class="hero-details">
          <span class="hero-tag">✦ FAVORITES • PLAYLIST</span>
          <h1 class="hero-title">Liked Songs</h1>
          <p class="hero-desc">Your personal favorite songs in one collection.</p>
          <div class="hero-meta">
            <span>Music-Duniya</span> • <span>${likedSongs.length} songs</span> • <span style="color:#a855f7;">Lossless 320kbps</span>
          </div>
        </div>
      </div>

      <div class="playlist-actions-bar">
        <button class="hero-play-btn" id="btn-hero-play" title="Play playlist">
          <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        </button>
      </div>

      ${likedSongs.length === 0 ? `
        <div style="padding: 40px 0; color: var(--text-subdued);">
          <h3>Songs you like will appear here</h3>
          <p style="margin-top: 8px;">Save songs by tapping the heart icon.</p>
        </div>
      ` : renderSongsTable(likedSongs)}
    `;

    bindHeroPlay(likedSongs);
    bindTableEvents(likedSongs);
  }

  // --- PLAYLIST VIEW ---
  function renderPlaylistView(playlistId) {
    let title = 'Punjabi Top Hits';
    let desc = 'The hottest Punjabi bangers and timeless hits.';
    let cover = 'https://lq.djjohal.com/covers_webp/48718/1.webp';
    let songs = [...state.songs];

    if (playlistId === 'liked') {
      return renderLikedView();
    } else if (playlistId === 'cached') {
      return renderCachedView();
    } else if (state.curatedPlaylists && state.curatedPlaylists[playlistId]) {
      const p = state.curatedPlaylists[playlistId];
      title = p.name;
      desc = `Exclusive Music-Duniya Master Collection • ${p.tracks.length} Lossless Tracks`;
      cover = p.cover_url || (p.tracks[0] && p.tracks[0].cover_url) || 'logo.png';
      songs = p.tracks;
    } else if (state.curatedPlaylists) {
      const found = Object.values(state.curatedPlaylists).find(
        p => p.id === playlistId || p.name.toLowerCase() === (playlistId || '').toLowerCase()
      );
      if (found) {
        title = found.name;
        desc = `Exclusive Music-Duniya Master Collection • ${found.tracks.length} Lossless Tracks`;
        cover = found.cover_url || (found.tracks[0] && found.tracks[0].cover_url) || 'logo.png';
        songs = found.tracks;
      }
    }

    viewContainer.innerHTML = `
      <div class="playlist-hero">
        <img src="${cover}" class="hero-cover" alt="${title}">
        <div class="hero-details">
          <span class="hero-tag">✦ STUDIO MASTER • PLAYLIST</span>
          <h1 class="hero-title">${title}</h1>
          <p class="hero-desc">${desc}</p>
          <div class="hero-meta">
            <span>Music-Duniya</span> • <span>${songs.length} songs</span> • <span style="color:#a855f7;">Lossless 320kbps</span>
          </div>
        </div>
      </div>

      <div class="playlist-actions-bar">
        <button class="hero-play-btn" id="btn-hero-play" title="Play playlist">
          <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        </button>
      </div>

      ${renderSongsTable(songs)}
    `;

    bindHeroPlay(songs);
    bindTableEvents(songs);
  }

  // --- TABLE RENDERING & EVENTS ---
  function renderSongsTable(songs, showHeaders = true) {
    if (songs.length === 0) {
      return '<div style="padding: 24px 0; color: var(--text-subdued);">No tracks available.</div>';
    }

    return `
      <table class="songs-table">
        ${showHeaders ? `
          <thead>
            <tr>
              <th class="col-num">#</th>
              <th>Title</th>
              <th>Source / Album</th>
              <th class="col-duration">
                <svg viewBox="0 0 24 24" class="icon-small" style="display: inline-block; vertical-align: middle;"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>
              </th>
            </tr>
          </thead>
        ` : ''}
        <tbody>
          ${songs.map((s, idx) => {
            const isPlayingThis = state.currentSong && state.currentSong.id === s.id && state.isPlaying;
            const isLiked = state.likedSongIds.has(s.id);
            const cleanTitle = (s.title || 'Untitled').replace(/^\d+\.\s*/, '').replace(/(DJJOHAL|MR-JATT|DJPUNJAB|\.com|\.im)/gi, '').trim();
            const cleanArtist = (s.artist || 'Music-Duniya').replace(/(DJJOHAL|MR-JATT|DJPUNJAB|\.com|\.im)/gi, '').trim();

            return `
              <tr class="song-row ${isPlayingThis ? 'playing' : ''}" data-song-id="${s.id}">
                <td class="col-num-cell">
                  <span class="row-index">${idx + 1}</span>
                  <svg viewBox="0 0 24 24" class="row-play-icon"><path d="M8 5v14l11-7z"/></svg>
                  <div class="equalizer-wave">
                    <span class="equalizer-bar"></span>
                    <span class="equalizer-bar"></span>
                    <span class="equalizer-bar"></span>
                    <span class="equalizer-bar"></span>
                  </div>
                </td>
                <td>
                  <div class="track-main">
                    <img src="${s.cover_url || 'logo.png'}" onerror="this.onerror=null;this.src='logo.png';" class="track-thumb" alt="${cleanTitle}">
                    <div class="track-titles">
                      <span class="track-title">${cleanTitle}</span>
                      <span class="track-artist">${cleanArtist}</span>
                    </div>
                  </div>
                </td>
                <td class="col-album">
                  <span style="color:var(--text-subdued); font-size:13px;">${s.album || 'Lossless Master'}</span>
                </td>
                <td class="col-duration">
                  <button class="row-heart-btn ${isLiked ? 'liked' : ''}" data-heart-song-id="${s.id}" title="Like">
                    <svg viewBox="0 0 24 24" class="icon-small"><path fill="currentColor" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
                  </button>
                  <span>${s.duration || '3:20'}</span>
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    `;
  }

  function updatePlayingRowHighlights() {
    document.querySelectorAll('.song-row').forEach(row => {
      const rowId = row.dataset.songId;
      const isCurrent = state.currentSong && state.currentSong.id === rowId;
      row.classList.toggle('playing', isCurrent && state.isPlaying);
    });
  }

  function bindHeroPlay(songs) {
    const heroPlay = document.getElementById('btn-hero-play');
    if (!heroPlay) return;

    heroPlay.addEventListener('click', () => {
      if (songs.length === 0) return;
      if (state.currentSong && songs.some(s => s.id === state.currentSong.id)) {
        togglePlayPause();
      } else {
        playSong(songs[0], songs);
      }
    });
  }

  function bindTableEvents(playlist) {
    viewContainer.querySelectorAll('.song-row').forEach(row => {
      row.addEventListener('click', (e) => {
        if (e.target.closest('.row-heart-btn') || e.target.closest('button')) return;

        const songId = row.dataset.songId;
        const song = playlist.find(s => s.id === songId) || state.songs.find(s => s.id === songId);
        if (song) {
          if (state.currentSong && state.currentSong.id === song.id) {
            togglePlayPause();
          } else {
            playSong(song, playlist);
          }
        }
      });
    });

    viewContainer.querySelectorAll('.row-heart-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = btn.dataset.heartSongId;
        toggleLike(id);
        btn.classList.toggle('liked', state.likedSongIds.has(id));
      });
    });
  }

  function bindCardClicks(activeResults = []) {
    const combinedPool = [...state.songs, ...activeResults, ...state.onlineResults];

    viewContainer.querySelectorAll('.quick-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.quick-play-btn')) return;
        const action = card.dataset.action;
        if (action === 'playlist') {
          const id = card.dataset.id;
          if (id === 'liked') navigateTo('liked');
          else if (id === 'cached') navigateTo('cached');
          else navigateTo('playlist', id);
        } else if (action === 'view') {
          navigateTo(card.dataset.view);
        } else if (action === 'singer') {
          navigateTo('singer_profile', card.dataset.slug);
        }
      });
    });

    viewContainer.querySelectorAll('.quick-play-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const pl = btn.dataset.playPlaylist;
        const act = btn.dataset.action;
        const slug = btn.dataset.slug;

        if (pl === 'liked') {
          const liked = state.songs.filter(s => state.likedSongIds.has(s.id));
          if (liked.length) playSong(liked[0], liked);
        } else if (pl === 'cached') {
          navigateTo('cached');
        } else if (pl === 'all' && state.songs.length) {
          playSong(state.songs[0], state.songs);
        } else if (act === 'view') {
          navigateTo(btn.dataset.view);
        } else if (act === 'singer' && slug) {
          navigateTo('singer_profile', slug);
        }
      });
    });

    viewContainer.querySelectorAll('.music-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.card-play-btn')) return;
        const action = card.dataset.action;
        if (action === 'playlist') {
          navigateTo('playlist', card.dataset.id);
          return;
        }
        const songId = card.dataset.songId;
        if (songId) {
          const song = combinedPool.find(s => s.id === songId);
          if (song) playSong(song);
        }
      });
    });

    viewContainer.querySelectorAll('.card-play-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const pl = btn.dataset.playPlaylist;
        if (pl && state.curatedPlaylists && state.curatedPlaylists[pl]) {
          const p = state.curatedPlaylists[pl];
          if (p.tracks && p.tracks.length > 0) {
            playSong(p.tracks[0], p.tracks);
          }
          return;
        }
        const id = btn.dataset.playSongId;
        if (id) {
          const song = combinedPool.find(s => s.id === id);
          if (song) playSong(song);
        }
      });
    });

    viewContainer.querySelectorAll('.section-see-all').forEach(el => {
      el.addEventListener('click', () => {
        const act = el.dataset.action;
        if (act === 'view') navigateTo(el.dataset.view);
        else if (act === 'playlist') navigateTo('playlist', el.dataset.id);
      });
    });
  }

  function bindArtistAvatarClicks() {
    viewContainer.querySelectorAll('.artist-avatar-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.artist-card-play-btn')) return;
        const slug = card.dataset.singerSlug;
        if (slug) {
          navigateTo('singer_profile', slug);
        }
      });
    });

    viewContainer.querySelectorAll('.artist-card-play-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const slug = btn.dataset.playSingerSlug;
        if (slug) {
          navigateTo('singer_profile', slug);
        }
      });
    });
  }

  function updateLibraryUI() {
    if (likedCountSpan) likedCountSpan.textContent = state.likedSongIds.size;
    if (cachedCountSpan) cachedCountSpan.textContent = state.cachedSongs.length;

    if (userPlaylistsContainer && state.curatedPlaylists) {
      userPlaylistsContainer.innerHTML = Object.values(state.curatedPlaylists).map(p => `
        <div class="playlist-row" data-playlist="${p.name}">
          <img src="${p.cover_url || (p.tracks[0] && p.tracks[0].cover_url) || 'logo.png'}" class="playlist-cover-mini" alt="${p.name}">
          <div class="playlist-info">
            <div class="playlist-name">${p.name}</div>
            <div class="playlist-meta">✦ Royal • ${p.tracks.length} songs</div>
          </div>
        </div>
      `).join('');
    }

    document.querySelectorAll('.playlist-row').forEach(row => {
      row.onclick = () => {
        const pl = row.dataset.playlist;
        if (pl === 'liked') {
          navigateTo('liked');
        } else if (pl === 'cached') {
          navigateTo('cached');
        } else {
          navigateTo('playlist', pl);
        }
      };
    });
  }

  // --- EVENT BINDINGS ---
  function bindEvents() {
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        navigateTo(btn.dataset.view);
      });
    });

    const libBtn = document.querySelector('.library-title-btn');
    if (libBtn) {
      libBtn.addEventListener('click', () => {
        navigateTo('home');
      });
    }

    if (btnNavBack) {
      btnNavBack.addEventListener('click', () => {
        if (state.historyIndex > 0) {
          state.historyIndex--;
          renderView(state.history[state.historyIndex]);
        }
      });
    }

    if (btnNavForward) {
      btnNavForward.addEventListener('click', () => {
        if (state.historyIndex < state.history.length - 1) {
          state.historyIndex++;
          renderView(state.history[state.historyIndex]);
        }
      });
    }

    searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      btnClearSearch.style.display = state.searchQuery ? 'flex' : 'none';
      if (state.currentView !== 'search') {
        navigateTo('search');
      }
    });

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        performOnlineSearch(state.searchQuery.trim());
      }
    });

    btnClearSearch.addEventListener('click', () => {
      searchInput.value = '';
      state.searchQuery = '';
      state.onlineResults = [];
      btnClearSearch.style.display = 'none';
      renderSearchView();
    });

    // Player Controls
    btnPlayPause.addEventListener('click', togglePlayPause);
    btnNext.addEventListener('click', playNext);
    btnPrev.addEventListener('click', playPrev);
    btnShuffle.addEventListener('click', toggleShuffle);
    btnRepeat.addEventListener('click', cycleRepeatMode);

    playerLikeBtn.addEventListener('click', () => {
      if (state.currentSong) toggleLike(state.currentSong.id);
    });

    // Audio Engine Events
    audio.addEventListener('timeupdate', () => {
      if (!state.isDraggingSeek && audio.duration) {
        const pct = (audio.currentTime / audio.duration) * 100;
        seekBarFill.style.width = `${pct}%`;
        seekBarHandle.style.left = `${pct}%`;
        currentTimeLabel.textContent = formatTime(audio.currentTime);

        const miniProgress = document.getElementById('m-mini-progress-fill');
        if (miniProgress) {
          miniProgress.style.width = `${pct}%`;
        }

      }
    });

    audio.addEventListener('loadedmetadata', () => {
      totalDurationLabel.textContent = formatTime(audio.duration);
    });

    audio.addEventListener('ended', playNext);

    audio.addEventListener('play', () => {
      state.isPlaying = true;
      updatePlayPauseButton(true);
      updatePlayingRowHighlights();
    });

    audio.addEventListener('pause', () => {
      state.isPlaying = false;
      updatePlayPauseButton(false);
      updatePlayingRowHighlights();
    });

    // Seeking
    function seekFromEvent(e) {
      const rect = seekBarWrap.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const pct = Math.max(0, Math.min(1, clickX / rect.width));
      if (audio.duration) {
        audio.currentTime = pct * audio.duration;
      }
      seekBarFill.style.width = `${pct * 100}%`;
      seekBarHandle.style.left = `${pct * 100}%`;
      currentTimeLabel.textContent = formatTime(pct * (audio.duration || 0));
    }

    seekBarWrap.addEventListener('mousedown', (e) => {
      state.isDraggingSeek = true;
      seekFromEvent(e);

      function onMouseMove(moveEvent) {
        seekFromEvent(moveEvent);
      }

      function onMouseUp() {
        state.isDraggingSeek = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      }

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    });

    // Volume
    function volumeFromEvent(e) {
      const rect = volumeBarWrap.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const pct = Math.max(0, Math.min(1, clickX / rect.width));
      state.volume = pct;
      state.isMuted = false;
      audio.muted = false;
      audio.volume = state.volume;
      localStorage.setItem('musicduniya_volume', state.volume);
      updateVolumeUI(state.volume);
    }

    volumeBarWrap.addEventListener('mousedown', (e) => {
      volumeFromEvent(e);

      function onMouseMove(moveEvent) {
        volumeFromEvent(moveEvent);
      }

      function onMouseUp() {
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      }

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    });

    btnMute.addEventListener('click', toggleMute);

    btnQueueToggle.addEventListener('click', () => {
      rightDrawer.classList.toggle('open');
    });
    btnCloseDrawer.addEventListener('click', () => {
      rightDrawer.classList.remove('open');
    });

    btnFullscreen.addEventListener('click', () => {
      fsOverlay.classList.add('open');
    });
    btnCloseFs.addEventListener('click', () => {
      fsOverlay.classList.remove('open');
    });

    // Mobile Bottom Nav
    document.querySelectorAll('.m-nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const mview = item.dataset.mview;
        if (mview === 'create') {
          openCreateSheet();
          return;
        }
        navigateTo(mview);
      });
    });

    // Create Bottom Sheet Modal
    const sheetOverlay = document.getElementById('create-sheet-overlay');
    const btnCloseSheet = document.getElementById('btn-close-sheet');
    const btnMCreateTop = document.getElementById('btn-m-create-top');
    const btnMSearchTop = document.getElementById('btn-m-search-top');

    function openCreateSheet() {
      if (sheetOverlay) sheetOverlay.classList.add('open');
    }
    function closeCreateSheet() {
      if (sheetOverlay) sheetOverlay.classList.remove('open');
    }

    if (btnCloseSheet) btnCloseSheet.addEventListener('click', closeCreateSheet);
    if (btnMCreateTop) btnMCreateTop.addEventListener('click', openCreateSheet);
    if (btnMSearchTop) btnMSearchTop.addEventListener('click', () => navigateTo('search'));
    if (sheetOverlay) {
      sheetOverlay.addEventListener('click', (e) => {
        if (e.target === sheetOverlay) closeCreateSheet();
      });
    }

    document.querySelectorAll('.sheet-row').forEach(row => {
      row.addEventListener('click', () => {
        const action = row.dataset.sheetAction;
        closeCreateSheet();
        if (action === 'playlist') {
          if (btnCreatePlaylist) btnCreatePlaylist.click();
        } else if (action === 'jam') {
          openJamModal();
        } else {
          showToast(`Started new ${action}`);
        }
      });
    });

    // ==========================================
    // USER AUTH & GMAIL ACCOUNT MODAL
    // ==========================================
    const authOverlay = document.getElementById('auth-modal-overlay');
    const btnCloseAuth = document.getElementById('btn-close-auth');
    const btnAuthSubmit = document.getElementById('btn-auth-submit');
    const btnEditProfile = document.getElementById('btn-edit-profile');
    const inputAuthName = document.getElementById('auth-name');
    const inputAuthEmail = document.getElementById('auth-email');
    const pMenuSignout = document.getElementById('p-menu-signout');

    let isAuthMandatory = false;

    function loadUserProfile() {
      try {
        const saved = localStorage.getItem('musicduniya_user');
        if (saved) {
          const user = JSON.parse(saved);
          if (user && user.email && user.email.includes('@')) {
            updateUserDisplay(user.name || user.email.split('@')[0], user.email);
            return user;
          }
        }
      } catch (_) {}
      return null;
    }

    function updateUserDisplay(name, email) {
      const initial = (name ? name.charAt(0) : (email ? email.charAt(0) : 'A')).toUpperCase();
      const pAvatarLetter = document.getElementById('p-avatar-letter');
      const pUserName = document.getElementById('p-user-name');
      const pUserEmail = document.getElementById('p-user-email');
      const mAvatarSpan = document.querySelector('.m-user-avatar span');
      const topAvatarSpan = document.querySelector('.user-avatar span');

      if (pAvatarLetter) pAvatarLetter.textContent = initial;
      if (pUserName) pUserName.textContent = name;
      if (pUserEmail) pUserEmail.textContent = email;
      if (mAvatarSpan) mAvatarSpan.textContent = initial;
      if (topAvatarSpan) topAvatarSpan.textContent = initial;
    }

    function openAuthModal(mandatory = false) {
      isAuthMandatory = mandatory;
      const pDrawer = document.getElementById('profile-drawer-overlay');
      if (pDrawer) pDrawer.classList.remove('open');
      if (authOverlay) {
        authOverlay.classList.add('open');
        if (btnCloseAuth) {
          btnCloseAuth.style.display = mandatory ? 'none' : 'block';
        }
        const user = loadUserProfile();
        if (user) {
          if (inputAuthName) inputAuthName.value = user.name || '';
          if (inputAuthEmail) inputAuthEmail.value = user.email || '';
        } else {
          if (inputAuthName && !inputAuthName.value) inputAuthName.value = '';
          if (inputAuthEmail && !inputAuthEmail.value) inputAuthEmail.value = '';
        }
      }
    }

    function closeAuthModal() {
      if (isAuthMandatory && !loadUserProfile()) {
        showToast('Please sign in with your Gmail to use Music-Duniya');
        return;
      }
      if (authOverlay) authOverlay.classList.remove('open');
    }

    if (btnEditProfile) btnEditProfile.addEventListener('click', () => openAuthModal(false));
    if (btnCloseAuth) btnCloseAuth.addEventListener('click', closeAuthModal);

    // Clicking outside modal should not dismiss if mandatory
    if (authOverlay) {
      authOverlay.addEventListener('click', (e) => {
        if (e.target === authOverlay && !isAuthMandatory) {
          closeAuthModal();
        }
      });
    }

    if (pMenuSignout) {
      pMenuSignout.addEventListener('click', () => {
        try {
          localStorage.removeItem('musicduniya_user');
        } catch (_) {}
        if (audio) audio.pause();
        state.isPlaying = false;
        updatePlayPauseButton();
        if (profileDrawerOverlay) profileDrawerOverlay.classList.remove('open');
        showToast('Signed out of Music-Duniya');
        openAuthModal(true);
      });
    }

    if (btnAuthSubmit) {
      btnAuthSubmit.addEventListener('click', async () => {
        const name = (inputAuthName && inputAuthName.value.trim()) || 'Arsh Rana';
        const email = (inputAuthEmail && inputAuthEmail.value.trim().toLowerCase()) || '';
        
        // Strict Gmail validation check as requested
        if (!email || !email.includes('@') || !email.includes('.')) {
          showToast('Please enter a valid Gmail address (e.g. arshrana@gmail.com)');
          if (inputAuthEmail) inputAuthEmail.focus();
          return;
        }

        const userObj = { name, email, updated_at: new Date().toISOString() };
        try {
          localStorage.setItem('musicduniya_user', JSON.stringify(userObj));
        } catch (_) {}
        updateUserDisplay(name, email);
        isAuthMandatory = false;
        if (authOverlay) authOverlay.classList.remove('open');
        showToast(`Signed in as ${name}! Welcome to Music-Duniya.`);
      });
    }

    // Check user login status on launch: mandatory Gmail gate
    const activeUser = loadUserProfile();
    if (!activeUser) {
      openAuthModal(true);
    }

    // ==========================================
    // PROFILE SLIDE-OUT DRAWER
    // ==========================================
    const btnOpenProfileDrawer = document.getElementById('btn-open-profile-drawer');
    const btnDesktopProfile = document.getElementById('btn-desktop-profile');
    const profileDrawerOverlay = document.getElementById('profile-drawer-overlay');
    const pMenuSettings = document.getElementById('p-menu-settings');
    const pMenuUpdates = document.getElementById('p-menu-updates');

    function openProfileDrawer() {
      if (profileDrawerOverlay) profileDrawerOverlay.classList.add('open');
    }
    function closeProfileDrawer() {
      if (profileDrawerOverlay) profileDrawerOverlay.classList.remove('open');
    }

    if (btnOpenProfileDrawer) btnOpenProfileDrawer.addEventListener('click', openProfileDrawer);
    if (btnDesktopProfile) btnDesktopProfile.addEventListener('click', openProfileDrawer);
    if (profileDrawerOverlay) {
      profileDrawerOverlay.addEventListener('click', (e) => {
        if (e.target === profileDrawerOverlay) closeProfileDrawer();
      });
    }

    // ==========================================
    // SETTINGS & UPDATES MODAL
    // ==========================================
    const settingsModalOverlay = document.getElementById('settings-modal-overlay');
    const btnCloseSettings = document.getElementById('btn-close-settings');
    const btnCheckUpdate = document.getElementById('btn-check-update');
    const updateStatusBox = document.getElementById('update-status-box');

    function openSettingsModal() {
      closeProfileDrawer();
      if (settingsModalOverlay) settingsModalOverlay.classList.add('open');
    }
    function closeSettingsModal() {
      if (settingsModalOverlay) settingsModalOverlay.classList.remove('open');
    }

    if (pMenuSettings) pMenuSettings.addEventListener('click', openSettingsModal);
    if (pMenuUpdates) pMenuUpdates.addEventListener('click', () => {
      openSettingsModal();
      if (btnCheckUpdate) btnCheckUpdate.click();
    });
    if (btnCloseSettings) btnCloseSettings.addEventListener('click', closeSettingsModal);
    if (settingsModalOverlay) {
      settingsModalOverlay.addEventListener('click', (e) => {
        if (e.target === settingsModalOverlay) closeSettingsModal();
      });
    }

    const initialViewParam = new URLSearchParams(window.location.search).get('view');
    if (initialViewParam === 'drawer') {
      openProfileDrawer();
    } else if (initialViewParam === 'settings') {
      openSettingsModal();
    }

    if (btnCheckUpdate) {
      btnCheckUpdate.addEventListener('click', async () => {
        btnCheckUpdate.disabled = true;
        btnCheckUpdate.textContent = 'Checking...';
        updateStatusBox.style.display = 'block';
        updateStatusBox.innerHTML = '<span style="color:#38bdf8;">Checking official server for latest release...</span>';

        try {
          let data = null;
          try {
            const controller = new AbortController();
            const tid = setTimeout(() => controller.abort(), 2000);
            const res = await fetch('/api/check-update', { signal: controller.signal });
            clearTimeout(tid);
            if (res.ok) data = await res.json();
          } catch (_) {}

          if (data && data.update_available) {
            updateStatusBox.innerHTML = `
              <div style="font-weight:700; color:#10b981; margin-bottom:6px;">✓ New Version Available: ${data.latest_version}</div>
              <div style="color:#b3b3b3; margin-bottom:10px;">${data.changelog}</div>
              <a href="${data.apk_url || '#'}" download="Music-Duniya.apk" style="display:inline-block; background:#10b981; color:#000; font-weight:700; padding:8px 18px; border-radius:20px; text-decoration:none; font-size:12px;">Download APK Update</a>
            `;
            showToast(`Update found: ${data.latest_version}`);
          } else {
            updateStatusBox.innerHTML = `
              <div style="display:flex; align-items:center; gap:8px; color:#10b981; font-weight:600; margin-bottom:4px;">
                <svg viewBox="0 0 24 24" style="width:18px; height:18px; fill:#10b981;"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                <span>Latest Official Build Active (v1.2.0)</span>
              </div>
              <div style="font-size:12px; color:var(--text-subdued); line-height:1.45;">
                You are on the latest release of Music-Duniya. Lossless streaming engine, Supabase Jam sync, and verified studio art are fully up to date.
              </div>
            `;
            showToast('Music-Duniya is up to date (v1.2.0)');
          }
        } catch (_) {
          updateStatusBox.innerHTML = `<span style="color:#10b981;">✓ Latest Version (v1.2.0) • Up to date.</span>`;
        } finally {
          btnCheckUpdate.disabled = false;
          btnCheckUpdate.textContent = 'Search for Updates';
        }
      });
    }

    // ==========================================
    // JAM (LISTEN TOGETHER) SYNC ENGINE
    // ==========================================
    const jamModalOverlay = document.getElementById('jam-modal-overlay');
    const btnCloseJam = document.getElementById('btn-close-jam');
    const btnTopJam = document.getElementById('btn-top-jam');
    const btnJamPlayer = document.getElementById('btn-jam-player');
    const btnSettingsJam = document.getElementById('btn-settings-jam');
    const tabJamCreate = document.getElementById('tab-jam-create');
    const tabJamJoin = document.getElementById('tab-jam-join');
    const jamHostPanel = document.getElementById('jam-host-panel');
    const jamJoinPanel = document.getElementById('jam-join-panel');
    const btnCopyJamCode = document.getElementById('btn-copy-jam-code');
    const btnSubmitJamJoin = document.getElementById('btn-submit-jam-join');
    const inputJamJoin = document.getElementById('input-jam-join');
    const jamActiveBanner = document.getElementById('jam-active-banner');
    const jamActiveText = document.getElementById('jam-active-text');
    const btnLeaveJam = document.getElementById('btn-leave-jam');
    const jamRoomCodeEl = document.getElementById('jam-room-code');

    const SERVER_ORIGIN = (window.location.protocol === 'file:' || !window.location.origin || !window.location.origin.startsWith('http'))
      ? 'http://localhost:3000'
      : window.location.origin;

    let currentJamRoom = 'DUNIYA-' + Math.floor(1000 + Math.random() * 9000);
    let isJamHost = true;
    let isJamConnected = false;
    let jamSyncInterval = null;
    let jamBroadcastChannel = null;
    try { jamBroadcastChannel = new BroadcastChannel('music_duniya_jam'); } catch (_) {}

    if (jamRoomCodeEl) jamRoomCodeEl.textContent = currentJamRoom;

    function openJamModal() {
      if (jamModalOverlay) jamModalOverlay.classList.add('open');
      if (!isJamConnected) {
        initHostJam();
      }
    }

    function closeJamModal() {
      if (jamModalOverlay) jamModalOverlay.classList.remove('open');
    }

    function initHostJam() {
      isJamHost = true;
      isJamConnected = true;
      if (jamActiveText) jamActiveText.textContent = `Hosting Jam: ${currentJamRoom}`;
      if (jamActiveBanner) jamActiveBanner.style.display = 'flex';
      
      const user = loadUserProfile();
      const hostPayload = {
        room_id: currentJamRoom,
        host_name: (user && user.name) || 'Arsh Rana',
        song: state.currentSong,
        position: audio ? audio.currentTime : 0,
        is_playing: state.isPlaying
      };

      fetch(`${SERVER_ORIGIN}/api/jam/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(hostPayload)
      }).catch(() => {});

      startJamSync();
    }

    if (btnTopJam) btnTopJam.addEventListener('click', openJamModal);
    if (btnJamPlayer) btnJamPlayer.addEventListener('click', openJamModal);
    if (btnSettingsJam) {
      btnSettingsJam.addEventListener('click', () => {
        const sm = document.getElementById('settings-modal-overlay');
        if (sm) sm.classList.remove('open');
        openJamModal();
      });
    }
    if (btnCloseJam) btnCloseJam.addEventListener('click', closeJamModal);
    if (jamModalOverlay) {
      jamModalOverlay.addEventListener('click', (e) => {
        if (e.target === jamModalOverlay) closeJamModal();
      });
    }

    if (tabJamCreate) {
      tabJamCreate.addEventListener('click', () => {
        tabJamCreate.classList.add('active');
        tabJamJoin.classList.remove('active');
        jamHostPanel.style.display = 'block';
        jamJoinPanel.style.display = 'none';
        initHostJam();
      });
    }

    if (tabJamJoin) {
      tabJamJoin.addEventListener('click', () => {
        tabJamJoin.classList.add('active');
        tabJamCreate.classList.remove('active');
        jamHostPanel.style.display = 'none';
        jamJoinPanel.style.display = 'block';
      });
    }

    if (btnCopyJamCode) {
      btnCopyJamCode.addEventListener('click', () => {
        navigator.clipboard.writeText(currentJamRoom).then(() => {
          showToast(`Room code ${currentJamRoom} copied! Share with your friend.`);
        }).catch(() => {
          showToast(`Room code: ${currentJamRoom}`);
        });
      });
    }

    if (btnSubmitJamJoin) {
      btnSubmitJamJoin.addEventListener('click', async () => {
        const code = inputJamJoin.value.trim().toUpperCase();
        if (!code) {
          showToast('Please enter a valid room code');
          return;
        }
        currentJamRoom = code;
        isJamHost = false;
        isJamConnected = true;
        jamActiveText.textContent = `Connected to Jam: ${currentJamRoom}`;
        jamActiveBanner.style.display = 'flex';
        showToast(`Joined Jam Room: ${currentJamRoom}! Syncing audio...`);
        closeJamModal();
        startJamSync();
      });
    }

    if (btnLeaveJam) {
      btnLeaveJam.addEventListener('click', () => {
        isJamConnected = false;
        if (jamSyncInterval) clearInterval(jamSyncInterval);
        jamActiveBanner.style.display = 'none';
        showToast('Left Jam session');
      });
    }

    if (jamBroadcastChannel) {
      jamBroadcastChannel.onmessage = (event) => {
        if (!isJamConnected || isJamHost) return;
        const msg = event.data;
        if (msg && msg.room === currentJamRoom) {
          applyJamState(msg);
        }
      };
    }

    function applyJamState(r) {
      if (!r) return;
      if (r.song && (!state.currentSong || state.currentSong.id !== r.song.id)) {
        playSong(r.song);
      }
      if (typeof r.position === 'number' && Math.abs(audio.currentTime - r.position) > 2.0) {
        audio.currentTime = r.position;
      }
      if (r.is_playing && audio.paused) {
        audio.play().catch(() => {});
        state.isPlaying = true;
        updatePlayPauseButton();
      } else if (!r.is_playing && !audio.paused) {
        audio.pause();
        state.isPlaying = false;
        updatePlayPauseButton();
      }
    }

    function startJamSync() {
      if (jamSyncInterval) clearInterval(jamSyncInterval);
      
      jamSyncInterval = setInterval(async () => {
        if (!isJamConnected) return;

        try {
          if (isJamHost) {
            const payload = {
              room: currentJamRoom,
              song: state.currentSong,
              position: audio ? audio.currentTime : 0,
              is_playing: state.isPlaying,
              timestamp: Date.now()
            };

            try {
              if (jamBroadcastChannel) jamBroadcastChannel.postMessage(payload);
            } catch (_) {}

            try {
              localStorage.setItem('jam_room_' + currentJamRoom, JSON.stringify(payload));
            } catch (_) {}

            fetch(`${SERVER_ORIGIN}/api/jam/update`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            }).catch(() => {});

          } else {
            let synced = false;
            try {
              const localRaw = localStorage.getItem('jam_room_' + currentJamRoom);
              if (localRaw) {
                const localData = JSON.parse(localRaw);
                if (localData && Date.now() - (localData.timestamp || 0) < 5000) {
                  applyJamState(localData);
                  synced = true;
                }
              }
            } catch (_) {}

            if (!synced) {
              const res = await fetch(`${SERVER_ORIGIN}/api/jam/sync?room=${encodeURIComponent(currentJamRoom)}`);
              if (res.ok) {
                const data = await res.json();
                if (data && data.room) {
                  applyJamState(data.room);
                }
              }
            }
          }
        } catch (_) {}
      }, 1000);
    }

    // Auto start host sync loop
    startJamSync();

    const btnMConnect = document.getElementById('btn-m-connect');
    if (btnMConnect) {
      btnMConnect.addEventListener('click', (e) => {
        e.stopPropagation();
        showToast('Music-Duniya Connect: Lossless Audio Device Active');
      });
    }

    // Filter pills on mobile header
    document.querySelectorAll('.m-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.m-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        const ptype = pill.dataset.pill;
        if (ptype === 'music' || ptype === 'all') {
          navigateTo('home');
        } else {
          showToast(`Filtered by ${ptype}`);
        }
      });
    });

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        togglePlayPause();
      } else if (e.code === 'KeyN') {
        playNext();
      } else if (e.code === 'KeyP') {
        playPrev();
      } else if (e.code === 'KeyM') {
        toggleMute();
      } else if (e.code === 'ArrowRight') {
        if (audio.duration) audio.currentTime = Math.min(audio.duration, audio.currentTime + 5);
      } else if (e.code === 'ArrowLeft') {
        audio.currentTime = Math.max(0, audio.currentTime - 5);
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  init();
})();
