<script setup>
/* Left-hand nav, replacing the old top pill-bar header, to match the
 * sidebar-dashboard reference layout. The search input is decorative
 * (styled to match) - there's nothing in this app to search yet - kept
 * disabled so it doesn't imply working functionality that isn't there. */
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <span class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
          <path d="M12 2 L4 13h6l-1 9 9-13h-6z" fill="var(--accent)" />
        </svg>
      </span>
      <span class="brand-name">Demo Kit</span>
    </div>

    <label class="search">
      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="7" />
        <path d="m21 21-4.3-4.3" stroke-linecap="round" />
      </svg>
      <input type="text" placeholder="Search" disabled />
    </label>

    <nav class="nav">
      <span class="nav-heading">Dashboard</span>

      <router-link to="/" class="nav-link">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M13 2 5 13h6l-1 9 9-13h-6z" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        Energy Monitoring
      </router-link>

      <router-link to="/predictive-maintenance" class="nav-link">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="4" y="4" width="16" height="16" rx="2.5" />
          <path d="M9 9h6v6H9z" />
          <path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2" stroke-linecap="round" />
        </svg>
        Predictive Maintenance
      </router-link>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 248px;
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border-soft);
  padding: 22px 18px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  min-height: 100vh;
}

.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-weight: 700;
  font-size: 15px;
  padding: 0 4px;
}

.brand-mark {
  display: inline-flex;
  width: 30px;
  height: 30px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--accent-soft);
}

.search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--surface-2);
  color: var(--text-faint);
}

.search input {
  border: none;
  background: transparent;
  outline: none;
  font-size: 13px;
  color: var(--text);
  width: 100%;
}

.search input::placeholder {
  color: var(--text-faint);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.nav-heading {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0 10px 4px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 11px 12px;
  border-radius: var(--radius-md);
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-muted);
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-link:hover {
  background: var(--surface-2);
}

.nav-link.router-link-exact-active {
  background: var(--accent-grad);
  color: #fff;
}

@media (max-width: 860px) {
  .sidebar {
    width: 100%;
    min-height: 0;
    border-right: none;
    border-bottom: 1px solid var(--border-soft);
  }
  .nav {
    flex-direction: row;
    flex-wrap: wrap;
  }
  .search {
    display: none;
  }
}
</style>
