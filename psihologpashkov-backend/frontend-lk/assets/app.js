(function () {
  const config = window.LK_CONFIG || {};
  const API_BASE_URL = String(config.API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");
  const API_ORIGIN = new URL(API_BASE_URL).origin;

  let accessToken = null;
  let currentUser = null;

  const elements = {
    message: document.getElementById("message"),
    authSection: document.getElementById("authSection"),
    profileSection: document.getElementById("profileSection"),
    loginForm: document.getElementById("loginForm"),
    registerForm: document.getElementById("registerForm"),
    profileForm: document.getElementById("profileForm"),
    passwordForm: document.getElementById("passwordForm"),
    avatarForm: document.getElementById("avatarForm"),
    logoutButton: document.getElementById("logoutButton"),
    deleteAvatarButton: document.getElementById("deleteAvatarButton"),
    profileEmail: document.getElementById("profileEmail"),
    profileName: document.getElementById("profileName"),
    avatarImage: document.getElementById("avatarImage")
  };

  class ApiError extends Error {
    constructor(status, payload) {
      const detail = payload && typeof payload === "object" ? payload.detail : payload;
      super(detail || `Ошибка API: ${status}`);
      this.status = status;
      this.payload = payload;
    }
  }

  function showMessage(text, isError = false) {
    elements.message.textContent = text;
    elements.message.classList.toggle("error", isError);
    elements.message.classList.remove("hidden");
  }

  function hideMessage() {
    elements.message.textContent = "";
    elements.message.classList.add("hidden");
    elements.message.classList.remove("error");
  }

  function setAuthenticatedView(isAuthenticated) {
    elements.authSection.classList.toggle("hidden", isAuthenticated);
    elements.profileSection.classList.toggle("hidden", !isAuthenticated);
    elements.logoutButton.classList.toggle("hidden", !isAuthenticated);
  }

  function getErrorMessage(error) {
    if (error instanceof ApiError) {
      if (Array.isArray(error.payload?.detail)) {
        return "Проверьте корректность заполнения формы.";
      }

      return String(error.payload?.detail || error.message);
    }

    return "Неожиданная ошибка. Проверьте подключение к API.";
  }

  async function apiRequest(path, options = {}) {
    const method = options.method || "GET";
    const retry = options.retry !== false;
    const headers = Object.assign({}, options.headers || {});
    const requestOptions = {
      method,
      headers,
      credentials: "include"
    };

    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    if (options.body instanceof FormData) {
      requestOptions.body = options.body;
    } else if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
      requestOptions.body = JSON.stringify(options.body);
    }

    const response = await fetch(`${API_BASE_URL}${path}`, requestOptions);

    if (response.status === 401 && retry && path !== "/auth/refresh" && path !== "/auth/login") {
      const refreshed = await refreshAccessToken();

      if (refreshed) {
        return apiRequest(path, Object.assign({}, options, { retry: false }));
      }
    }

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      throw new ApiError(response.status, payload);
    }

    return payload;
  }

  async function refreshAccessToken() {
    try {
      const tokenPair = await apiRequest("/auth/refresh", {
        method: "POST",
        retry: false
      });

      accessToken = tokenPair.access_token;
      return true;
    } catch (_) {
      accessToken = null;
      return false;
    }
  }

  async function loadCurrentUser() {
    currentUser = await apiRequest("/me");
    renderCurrentUser(currentUser);
    setAuthenticatedView(true);
  }

  function renderCurrentUser(user) {
    elements.profileEmail.textContent = user.email;
    elements.profileName.textContent = user.full_name || "Имя не указано";
    elements.profileForm.elements.full_name.value = user.full_name || "";

    if (user.avatar_path) {
      elements.avatarImage.src = `${API_ORIGIN}${user.avatar_path}`;
      elements.avatarImage.classList.remove("hidden");
    } else {
      elements.avatarImage.removeAttribute("src");
      elements.avatarImage.classList.add("hidden");
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    hideMessage();

    const formData = new FormData(elements.loginForm);

    try {
      const tokenPair = await apiRequest("/auth/login", {
        method: "POST",
        body: {
          email: formData.get("email"),
          password: formData.get("password")
        }
      });

      accessToken = tokenPair.access_token;
      await loadCurrentUser();
      elements.loginForm.reset();
      showMessage("Вы вошли в личный кабинет.");
    } catch (error) {
      showMessage(getErrorMessage(error), true);
    }
  }

  async function handleRegister(event) {
    event.preventDefault();
    hideMessage();

    const formData = new FormData(elements.registerForm);
    const email = formData.get("email");
    const password = formData.get("password");

    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: {
          email,
          password,
          full_name: formData.get("full_name") || null
        }
      });

      elements.registerForm.reset();
      showMessage("Аккаунт создан. Проверьте почту и подтвердите email.");
    } catch (error) {
      showMessage(getErrorMessage(error), true);
    }
  }

  async function handleProfileUpdate(event) {
    event.preventDefault();
    hideMessage();

    const formData = new FormData(elements.profileForm);

    try {
      currentUser = await apiRequest("/me", {
        method: "PATCH",
        body: {
          full_name: formData.get("full_name") || null
        }
      });

      renderCurrentUser(currentUser);
      showMessage("Профиль сохранён.");
    } catch (error) {
      showMessage(getErrorMessage(error), true);
    }
  }

  async function handlePasswordChange(event) {
    event.preventDefault();
    hideMessage();

    const formData = new FormData(elements.passwordForm);

    try {
      await apiRequest("/me/password", {
        method: "PATCH",
        body: {
          current_password: formData.get("current_password"),
          new_password: formData.get("new_password")
        }
      });

      elements.passwordForm.reset();
      showMessage("Пароль изменён. При следующем обновлении сессии потребуется повторный вход.");
    } catch (error) {
      showMessage(getErrorMessage(error), true);
    }
  }

  async function handleAvatarUpload(event) {
    event.preventDefault();
    hideMessage();

    const fileInput = elements.avatarForm.elements.file;

    if (!fileInput.files.length) {
      showMessage("Выберите файл аватара.", true);
      return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
      currentUser = await apiRequest("/me/avatar", {
        method: "PATCH",
        body: formData
      });

      renderCurrentUser(currentUser);
      elements.avatarForm.reset();
      showMessage("Аватар обновлён.");
    } catch (error) {
      showMessage(getErrorMessage(error), true);
    }
  }

  async function handleAvatarDelete() {
    hideMessage();

    try {
      currentUser = await apiRequest("/me/avatar", {
        method: "DELETE"
      });

      renderCurrentUser(currentUser);
      showMessage("Аватар удалён.");
    } catch (error) {
      showMessage(getErrorMessage(error), true);
    }
  }

  async function handleLogout() {
    hideMessage();

    try {
      await apiRequest("/auth/logout", {
        method: "POST"
      });
    } catch (_) {
      // Logout должен быть безопасным и идемпотентным для пользователя.
    }

    accessToken = null;
    currentUser = null;
    setAuthenticatedView(false);
    showMessage("Вы вышли из личного кабинета.");
  }

  async function confirmEmailFromUrl() {
    const url = new URL(window.location.href);
    const token = url.searchParams.get("token");

    if (!token) {
      return false;
    }

    try {
      await apiRequest(`/auth/verify-email?token=${encodeURIComponent(token)}`, {
        method: "GET",
        retry: false
      });

      url.searchParams.delete("token");
      window.history.replaceState({}, document.title, url.toString());
      showMessage("Email подтверждён. Теперь можно войти.");
      return true;
    } catch (error) {
      showMessage(getErrorMessage(error), true);
      return true;
    }
  }

  async function bootstrap() {
    setAuthenticatedView(false);

    const emailConfirmed = await confirmEmailFromUrl();

    if (emailConfirmed) {
      return;
    }

    const refreshed = await refreshAccessToken();

    if (!refreshed) {
      return;
    }

    try {
      await loadCurrentUser();
    } catch (_) {
      accessToken = null;
      setAuthenticatedView(false);
    }
  }

  elements.loginForm.addEventListener("submit", handleLogin);
  elements.registerForm.addEventListener("submit", handleRegister);
  elements.profileForm.addEventListener("submit", handleProfileUpdate);
  elements.passwordForm.addEventListener("submit", handlePasswordChange);
  elements.avatarForm.addEventListener("submit", handleAvatarUpload);
  elements.deleteAvatarButton.addEventListener("click", handleAvatarDelete);
  elements.logoutButton.addEventListener("click", handleLogout);

  bootstrap();
})();