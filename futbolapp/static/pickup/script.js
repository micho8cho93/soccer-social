// ============================================
// Configuration
// ============================================
const resolveRuntimeDefaults = () => {
  const { hostname, origin } = window.location;
  const isLocalDevelopment = hostname === 'localhost' || hostname === '127.0.0.1';
  const isGitHubPages = hostname.endsWith('github.io');

  return {
    environment: isLocalDevelopment ? 'development' : 'production',
    frontendUrl: new URL('/pickup/', origin).toString(),
    backendBaseUrl: isLocalDevelopment
      ? 'http://localhost:8000'
      : isGitHubPages
        ? 'https://testliga.up.railway.app'
        : origin,
    apiPaths: {
      games: '/futbol/api/games',
      players: '/futbol/api/game-players',
      health: '/futbol/api/health'
    }
  };
};

const DEFAULT_RUNTIME_CONFIG = {
  ...resolveRuntimeDefaults(),
  apiPaths: {
    games: '/futbol/api/games',
    players: '/futbol/api/game-players',
    health: '/futbol/api/health'
  }
};

const CONFIG = {
  ENVIRONMENT: DEFAULT_RUNTIME_CONFIG.environment,
  FRONTEND_URL: DEFAULT_RUNTIME_CONFIG.frontendUrl,
  BACKEND_BASE_URL: DEFAULT_RUNTIME_CONFIG.backendBaseUrl,
  API_BASE_URL: `${DEFAULT_RUNTIME_CONFIG.backendBaseUrl}${DEFAULT_RUNTIME_CONFIG.apiPaths.games}`,
  API_PLAYERS_URL: `${DEFAULT_RUNTIME_CONFIG.backendBaseUrl}${DEFAULT_RUNTIME_CONFIG.apiPaths.players}`,
  API_HEALTH_URL: `${DEFAULT_RUNTIME_CONFIG.backendBaseUrl}${DEFAULT_RUNTIME_CONFIG.apiPaths.health}`
};

const ensureTrailingSlash = (url) => (url.endsWith('/') ? url : `${url}/`);

const runtimeConfig = {
  async load() {
    const embeddedConfig = window.PICKUP_RUNTIME_CONFIG;

    if (embeddedConfig) {
      const merged = this.mergeWithDefaults({
        currentEnvironment: embeddedConfig.environment || DEFAULT_RUNTIME_CONFIG.environment,
        environments: {
          [embeddedConfig.environment || DEFAULT_RUNTIME_CONFIG.environment]: embeddedConfig
        }
      });
      this.apply(merged);
      console.info(`[startup] Loaded embedded runtime config for "${CONFIG.ENVIRONMENT}"`);
      return;
    }

    try {
      const response = await fetch(new URL('./config.json', import.meta.url), { cache: 'no-store' });

      if (!response.ok) {
        throw new Error(`Unable to load config.json (status ${response.status})`);
      }

      const fileConfig = await response.json();
      const merged = this.mergeWithDefaults(fileConfig);
      this.apply(merged);
      console.info(`[startup] Loaded runtime config for "${CONFIG.ENVIRONMENT}" from config.json`);
    } catch (error) {
      console.warn(`[startup] ${error.message}. Falling back to embedded defaults.`);
      this.apply(DEFAULT_RUNTIME_CONFIG);
    }
  },

  mergeWithDefaults(fileConfig) {
    const selectedEnvironment = fileConfig?.currentEnvironment || DEFAULT_RUNTIME_CONFIG.environment;
    const selectedEnvConfig = fileConfig?.environments?.[selectedEnvironment] || {};

    return {
      environment: selectedEnvironment,
      frontendUrl: selectedEnvConfig.frontendUrl || DEFAULT_RUNTIME_CONFIG.frontendUrl,
      backendBaseUrl: selectedEnvConfig.backendBaseUrl || DEFAULT_RUNTIME_CONFIG.backendBaseUrl,
      apiPaths: {
        ...DEFAULT_RUNTIME_CONFIG.apiPaths,
        ...(selectedEnvConfig.apiPaths || {})
      }
    };
  },

  apply(nextConfig) {
    CONFIG.ENVIRONMENT = nextConfig.environment;
    CONFIG.FRONTEND_URL = nextConfig.frontendUrl;
    CONFIG.BACKEND_BASE_URL = nextConfig.backendBaseUrl;
    CONFIG.API_BASE_URL = `${nextConfig.backendBaseUrl}${nextConfig.apiPaths.games}`;
    CONFIG.API_PLAYERS_URL = ensureTrailingSlash(`${nextConfig.backendBaseUrl}${nextConfig.apiPaths.players}`);
    CONFIG.API_HEALTH_URL = `${nextConfig.backendBaseUrl}${nextConfig.apiPaths.health}`;
  }
};

// ============================================
// State Management
// ============================================
const state = {
  games: [],
  selectedDay: null,
  registeringGameId: null,
  backendMetadata: null
};

// ============================================
// DOM Elements Cache
// ============================================
const DOM = {
  daysGrid: document.getElementById('days-grid'),
  gamesListContainer: document.getElementById('games-list'),
  selectedDayText: document.getElementById('selected-day'),
  modal: document.getElementById('registration-modal'),
  modalClose: document.getElementById('modal-close'),
  gameTitleSpan: document.getElementById('game-title-modal'),
  registrationForm: document.getElementById('registration-form'),
  playersModal: document.getElementById('players-modal'),
  playersModalClose: document.getElementById('players-modal-close'),
  playersGameTitleSpan: document.getElementById('players-game-title-modal'),
  playersList: document.getElementById('players-list')
};

// ============================================
// Utility Functions
// ============================================
const utils = {
  formatGameTime(startIsoString, endIsoString) {
    const timeOptions = { hour: 'numeric', minute: '2-digit', hour12: true };
    const startTime = new Date(startIsoString);

    if (Number.isNaN(startTime.getTime())) {
      return 'Time TBD';
    }

    const start = startTime.toLocaleTimeString('en-US', timeOptions);

    if (!endIsoString) {
      return start;
    }

    const endTime = new Date(endIsoString);

    if (Number.isNaN(endTime.getTime())) {
      return start;
    }

    const end = endTime.toLocaleTimeString('en-US', timeOptions);

    return `${start} - ${end}`;
  },

  formatGamePrice(priceValue) {
    if (priceValue === null || priceValue === undefined || priceValue === '') {
      return 'Price TBD';
    }

    const numericPrice = Number(priceValue);

    if (Number.isFinite(numericPrice)) {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
      }).format(numericPrice);
    }

    return String(priceValue);
  },

  normalizePhoneNumber(phoneNumber) {
    return String(phoneNumber || '').replace(/[^\d]/g, '');
  },

  formatDayAndDate(isoString) {
    const date = new Date(isoString);
    const dayName = date.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();
    const dayDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    return { dayName, dayDate };
  },

  getDayFromDate(isoString) {
    return new Date(isoString).toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();
  },

  getDayKey(date) {
    return date.toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();
  },

  getCurrentDayKey() {
    return this.getDayKey(new Date());
  },

  capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
  },

  getVisibleDates() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return Array.from({ length: 7 }, (_, index) => {
      const date = new Date(today);
      date.setDate(today.getDate() + index);
      return date;
    });
  },

  getVisibleRange() {
    const visibleDates = this.getVisibleDates();
    const rangeStart = new Date(visibleDates[0]);
    rangeStart.setHours(0, 0, 0, 0);

    const rangeEnd = new Date(visibleDates[6]);
    rangeEnd.setHours(23, 59, 59, 999);

    return { rangeStart, rangeEnd };
  },

  filterGamesForVisibleRange(games) {
    const { rangeStart, rangeEnd } = this.getVisibleRange();

    return games.filter(game => {
      const gameDate = new Date(game.time);
      return gameDate >= rangeStart && gameDate <= rangeEnd;
    });
  }
};

// ============================================
// API Functions
// ============================================
const api = {
  async fetchBackendMetadata() {
    try {
      const response = await fetch(CONFIG.API_HEALTH_URL, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const metadata = await response.json();
      state.backendMetadata = metadata;

      console.info('[startup] Environment wiring confirmed:', {
        frontend_environment: CONFIG.ENVIRONMENT,
        frontend_url: CONFIG.FRONTEND_URL,
        backend_url: CONFIG.BACKEND_BASE_URL,
        backend_environment: metadata.environment || 'unknown',
        backend_commit: metadata.commit || metadata.commit_hash || 'unknown'
      });
    } catch (error) {
      console.warn(`[startup] Could not load backend metadata from ${CONFIG.API_HEALTH_URL}: ${error.message}`);
    }
  },

  // GET all games from Django backend
  async fetchGames() {
    try {
      const response = await fetch(CONFIG.API_BASE_URL, {
        credentials: 'include', // needed if backend requires auth/cookies
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const games = await response.json();
      const visibleGames = utils.filterGamesForVisibleRange(games);
      const visibleDayKeys = utils.getVisibleDates().map(date => utils.getDayKey(date));
      const todayKey = utils.getCurrentDayKey();

      if (!state.selectedDay || !visibleDayKeys.includes(state.selectedDay)) {
        state.selectedDay = todayKey;
      }

      state.games = visibleGames;
      ui.renderDayCards(visibleGames);
      ui.renderGames(visibleGames);
      ui.showSelectedGames(state.selectedDay);
      ui.attachJoinButtonListeners();
    } catch (error) {
      console.error('Could not fetch pickup games:', error);
      ui.showError('Error loading games. Please check your connection and try again.');
    }
  },

  // POST registration to Django backend
  async submitRegistration(formData) {
    if (!state.registeringGameId) {
      ui.showAlert('Error: No game selected for registration.');
      return;
    }

    const pickupGameId = parseInt(state.registeringGameId, 10);
    const requestPayload = {
      pickup_game: pickupGameId,
      first_name: formData.first_name,
      last_name: formData.last_name,
      email: formData.email,
      phone_number: formData.phone_number,
      player_level: formData.player_level
    };

    console.debug('[registration] submitting payload:', {
      pickup_game: requestPayload.pickup_game,
      first_name: requestPayload.first_name,
      email: requestPayload.email
    });

    try {
      const response = await fetch(ensureTrailingSlash(CONFIG.API_PLAYERS_URL), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload),
        credentials: 'include'
      });

      const responseData = await response.json().catch(() => null);

      if (response.ok) {
        console.debug('[registration] backend response:', responseData);

        const normalizedResponse = Array.isArray(responseData) ? responseData[0] : responseData;

        const resolvedPickupGameId = Number(
          typeof normalizedResponse?.pickup_game === 'object'
            ? normalizedResponse?.pickup_game?.id
            : normalizedResponse?.pickup_game
        );

        const hasRequiredFields = Boolean(normalizedResponse?.id) && Number.isFinite(resolvedPickupGameId);
        const isExpectedGame = resolvedPickupGameId === pickupGameId;

        if (!hasRequiredFields || !isExpectedGame) {
          throw new Error(`Registration validation failed. Backend payload: ${JSON.stringify(responseData)}`);
        }

        ui.showAlert('Registration successful! You have been signed up for the game.');
        // Reset the form
        DOM.registrationForm.reset();
        // Clear any validation errors
        DOM.registrationForm.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
        DOM.registrationForm.querySelectorAll('.error-message').forEach(el => el.textContent = '');
        modal.close();
        // Re-fetch games to update player count
        await api.fetchGames();
      } else {
        const errorData = responseData || { error: 'Registration failed! Try again.' };
        // Log the error for debugging
        console.error('Registration error:', errorData);
        throw new Error(errorData.error || errorData.detail || errorData.pickup_game || 'Registration failed! Try again.');
      }
    } catch (error) {
      ui.showAlert(`Registration failed: ${error.message}`);
    }
  },

  // GET players for a specific game
  async fetchPlayersForGame(gameId) {
    try {
      const response = await fetch(`${ensureTrailingSlash(CONFIG.API_PLAYERS_URL)}?pickup_game=${encodeURIComponent(gameId)}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const responseBody = await response.json();

      // Handle common DRF list/pagination response shapes
      if (Array.isArray(responseBody)) {
        return responseBody.filter(player => Number(player?.pickup_game?.id ?? player?.pickup_game) === Number(gameId));
      }

      if (Array.isArray(responseBody?.results)) {
        return responseBody.results.filter(player => Number(player?.pickup_game?.id ?? player?.pickup_game) === Number(gameId));
      }

      // Fallback for legacy game detail serializer that embeds players
      if (Array.isArray(responseBody?.players)) {
        return responseBody.players;
      }

      return [];
    } catch (error) {
      console.error('Could not fetch players:', error);
      throw error;
    }
  }
};

// ============================================
// UI Rendering Functions
// ============================================
const ui = {
  renderDayCards(games) {
    const visibleDates = utils.getVisibleDates();
    const gameCounts = this.calculateGameCounts(games);
    const gamesByDay = this.groupGamesByDay(games);

    DOM.daysGrid.innerHTML = visibleDates.map((date) => {
      const day = utils.getDayKey(date);
      const count = gameCounts[day] || 0;
      const dayName = date.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();
      const dayDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const isActive = day === state.selectedDay ? 'active' : '';
      const mobileGames = this.createMobileDayGames(day, gamesByDay[day]);

      return `
        <div class="day-card-stack">
          <button class="day-card ${isActive}" data-day="${day}" aria-expanded="${day === state.selectedDay}" aria-controls="mobile-games-${day}">
            <span class="day-name">${dayName}</span>
            <span class="day-date">${dayDate}</span>
            <span class="game-count">${count} game${count !== 1 ? 's' : ''}</span>
          </button>
          <div class="day-card-games ${isActive}" id="mobile-games-${day}" data-day-panel="${day}">
            ${mobileGames}
          </div>
        </div>
      `;
    }).join('');

    this.attachDayCardListeners();
  },

  calculateGameCounts(games) {
    return games.reduce((counts, game) => {
      const day = utils.getDayFromDate(game.time);
      counts[day] = (counts[day] || 0) + 1;
      return counts;
    }, {});
  },

  renderGames(games) {
    const gamesByDay = this.groupGamesByDay(games);
    const visibleDayKeys = utils.getVisibleDates().map(date => utils.getDayKey(date));

    DOM.gamesListContainer.innerHTML = visibleDayKeys.map(day => `
      <div class="game-cards" data-day="${day}" style="display: ${day === state.selectedDay ? 'grid' : 'none'}">
        ${gamesByDay[day] ? gamesByDay[day].map(game => this.createGameCard(game)).join('') : '<p class="no-games">No games scheduled for this day.</p>'}
      </div>
    `).join('');
  },

  createMobileDayGames(day, gamesForDay = []) {
    if (!gamesForDay.length) {
      return '<p class="no-games no-games--mobile">No games scheduled for this day.</p>';
    }

    return `
      <div class="game-cards game-cards--mobile" data-day="${day}">
        ${gamesForDay.map(game => this.createGameCard(game)).join('')}
      </div>
    `;
  },

  groupGamesByDay(games) {
    return games.reduce((grouped, game) => {
      const day = utils.getDayFromDate(game.time);
      if (!grouped[day]) grouped[day] = [];
      grouped[day].push(game);
      return grouped;
    }, {});
  },

  createGameCard(game) {
    const maxPlayers = Number(game.max_players) || 0;
    const currentPlayers = Number(game.current_players) || 0;
    const spotsLeft = Math.max(0, maxPlayers - currentPlayers);
    const isFull = spotsLeft === 0;
    const gameType = game.sport || 'Soccer';
    const gamePrice = utils.formatGamePrice(game.price);

    return `
      <article class="game-card">
        <div class="game-header">
          <span class="game-type">${gameType}</span>
          <span class="spots-left">${isFull ? 'Game full' : `${spotsLeft} spot${spotsLeft !== 1 ? 's' : ''} left`}</span>
        </div>
        <h3 class="game-title">${game.location} Pickup</h3>
        <div class="game-info">
          <p class="game-time">${utils.formatGameTime(game.time, game.end_time)}</p>
          <p class="game-location">${game.location}</p>
          <p class="game-price">${gamePrice}</p>
        </div>
        <div class="game-buttons">
          <button class="join-btn" data-game-id="${game.id}" data-game-title="${game.location} Pickup" ${isFull ? 'disabled aria-disabled="true"' : ''}>
            ${isFull ? 'Game Full' : 'Join Game'}
          </button>
          <button class="players-btn" data-game-id="${game.id}" data-game-title="${game.location} Pickup">
            List of Players
          </button>
        </div>
      </article>
    `;
  },

  showSelectedGames(selectedDay) {
    document.querySelectorAll('.game-cards').forEach(cards => {
      if (cards.classList.contains('game-cards--mobile')) {
        return;
      }

      cards.style.display = cards.dataset.day === selectedDay ? 'grid' : 'none';
    });

    document.querySelectorAll('.day-card').forEach(card => {
      const isSelected = card.dataset.day === selectedDay;
      card.classList.toggle('active', isSelected);
      card.setAttribute('aria-expanded', String(isSelected));
    });

    document.querySelectorAll('.day-card-games').forEach(panel => {
      panel.classList.toggle('active', panel.dataset.dayPanel === selectedDay);
    });

    DOM.selectedDayText.textContent = utils.capitalizeFirstLetter(selectedDay);
    state.selectedDay = selectedDay;
  },

  showError(message) {
    DOM.gamesListContainer.innerHTML = `
      <div class="error-message-box">
        <p>${message}</p>
      </div>
    `;
  },

  showAlert(message) {
    alert(message);
    // TODO: Replace with custom toast notification
  },

  attachDayCardListeners() {
    document.querySelectorAll('.day-card').forEach(card => {
      card.addEventListener('click', function() {
        ui.showSelectedGames(this.dataset.day);
      });
    });
  },

  attachJoinButtonListeners() {
    document.querySelectorAll('.join-btn').forEach(button => {
      button.addEventListener('click', function() {
        if (this.disabled) {
          return;
        }

        state.registeringGameId = this.dataset.gameId;
        DOM.gameTitleSpan.textContent = this.dataset.gameTitle;
        modal.open();
      });
    });

    document.querySelectorAll('.players-btn').forEach(button => {
      button.addEventListener('click', function() {
        const gameId = this.dataset.gameId;
        const gameTitle = this.dataset.gameTitle;
        playersModal.open(gameId, gameTitle);
      });
    });
  }
};

// ============================================
// Modal Controller
// ============================================
const modal = {
  open() {
    DOM.modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  },

  close() {
    DOM.modal.classList.remove('active');
    document.body.style.overflow = 'auto';
    DOM.registrationForm.reset();
    this.clearErrors();
    state.registeringGameId = null;
  },

  clearErrors() {
    document.querySelectorAll('.error-message').forEach(el => el.textContent = '');
    document.querySelectorAll('.form-group input, .form-group select').forEach(field => {
      field.classList.remove('error');
    });
  }
};

// ============================================
// Players Modal Controller
// ============================================
const playersModal = {
  async open(gameId, gameTitle) {
    DOM.playersGameTitleSpan.textContent = gameTitle;
    DOM.playersModal.classList.add('active');
    document.body.style.overflow = 'hidden';

    // Show loading state
    DOM.playersList.innerHTML = `
      <div class="loading-spinner">
        <div class="spinner"></div>
        <p>Loading players...</p>
      </div>
    `;

    try {
      const players = await api.fetchPlayersForGame(gameId);
      this.renderPlayers(players);
    } catch (error) {
      DOM.playersList.innerHTML = `
        <div class="error-message-box">
          <p>Error loading players. Please try again.</p>
        </div>
      `;
    }
  },

  renderPlayers(players) {
    if (players.length === 0) {
      DOM.playersList.innerHTML = '<p class="no-games">No players signed up yet.</p>';
      return;
    }

    const playersHTML = players.map(player => {
      const firstName = player.first_name || player.user?.first_name || 'Player';

      return `
      <div class="player-item">
        <span class="player-name">${firstName}</span>
      </div>
    `;
    }).join('');

    DOM.playersList.innerHTML = `
      <div class="players-container">
        ${playersHTML}
      </div>
    `;
  },

  close() {
    DOM.playersModal.classList.remove('active');
    document.body.style.overflow = 'auto';
    DOM.playersList.innerHTML = '';
  }
};

// ============================================
// Form Validation
// ============================================
const validation = {
  rules: {
    'first-name': {
      required: true,
      minLength: 2,
      message: 'First name must be at least 2 characters'
    },
    'last-name': {
      required: true,
      minLength: 2,
      message: 'Last name must be at least 2 characters'
    },
    'email': {
      required: true,
      pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      message: 'Please enter a valid email address'
    },
    'phone': {
      required: true,
      pattern: /^[\d\s\-\(\)]+$/,
      message: 'Please enter a valid WhatsApp number'
    },
    'country-code': {
      required: true,
      pattern: /^\+[1-9]\d{0,3}$/,
      message: 'Please enter a valid country code like +34'
    },
    'player-level': {
      required: true,
      message: 'Please choose a player level'
    }
  },

  validateField(input) {
    const rule = this.rules[input.name];
    if (!rule) return true;

    const value = input.value.trim();
    const errorElement = input.parentElement.querySelector('.error-message');

    if (rule.required && !value) {
      this.showError(input, errorElement, rule.message || 'This field is required');
      return false;
    }

    if (rule.minLength && value.length < rule.minLength) {
      this.showError(input, errorElement, rule.message);
      return false;
    }

    if (rule.pattern && !rule.pattern.test(value)) {
      this.showError(input, errorElement, rule.message);
      return false;
    }

    this.clearError(input, errorElement);
    return true;
  },

  showError(input, errorElement, message) {
    input.classList.add('error');
    errorElement.textContent = message;
  },

  clearError(input, errorElement) {
    input.classList.remove('error');
    errorElement.textContent = '';
  },

  validateForm(form) {
    const inputs = form.querySelectorAll('input[required], select[required]');
    let isValid = true;

    inputs.forEach(input => {
      if (!this.validateField(input)) {
        isValid = false;
      }
    });

    return isValid;
  }
};

// ============================================
// Event Listeners Setup
// ============================================
const events = {
  init() {
    // Modal close events
    DOM.modalClose.addEventListener('click', () => modal.close());
    DOM.modal.querySelector('.modal-overlay').addEventListener('click', () => modal.close());
    DOM.modal.querySelector('.modal-content').addEventListener('click', (e) => e.stopPropagation());

    // Players modal close events
    DOM.playersModalClose.addEventListener('click', () => playersModal.close());
    DOM.playersModal.querySelector('.modal-overlay').addEventListener('click', () => playersModal.close());
    DOM.playersModal.querySelector('.modal-content').addEventListener('click', (e) => e.stopPropagation());

    // ESC key to close modals
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (DOM.modal.classList.contains('active')) {
          modal.close();
        }
        if (DOM.playersModal.classList.contains('active')) {
          playersModal.close();
        }
      }
    });

    // Form submission
    DOM.registrationForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      if (!validation.validateForm(DOM.registrationForm)) {
        return;
      }

      const formData = {
        first_name: document.getElementById('first-name').value.trim(),
        last_name: document.getElementById('last-name').value.trim(),
        email: document.getElementById('email').value.trim(),
        country_code: document.getElementById('country-code').value.trim(),
        phone_number: `${document.getElementById('country-code').value.trim()}${utils.normalizePhoneNumber(document.getElementById('phone').value)}`,
        player_level: document.getElementById('player-level').value
      };

      await api.submitRegistration(formData);
    });

    // Real-time validation
    DOM.registrationForm.querySelectorAll('input, select').forEach(field => {
      field.addEventListener('blur', () => validation.validateField(field));
      field.addEventListener('change', () => {
        if (field.classList.contains('error')) {
          validation.validateField(field);
        }
      });
      field.addEventListener('input', () => {
        if (field.classList.contains('error')) {
          validation.validateField(field);
        }
      });
    });
  }
};

// ============================================
// Application Initialization
// ============================================
const app = {
  async init() {
    await runtimeConfig.load();
    console.log('🚀 Pickup Games App Initialized');
    events.init();
    await api.fetchBackendMetadata();
    await api.fetchGames();
  }
};

// Start the application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => app.init());
} else {
  app.init();
}
