import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';

const require = createRequire(import.meta.url);

// Compile actual source and substitute only its external dependencies.
function loadSource(path, mocks = {}) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  });
  const module = { exports: {} };
  vm.runInNewContext(outputText, {
    module,
    exports: module.exports,
    require: name => Object.hasOwn(mocks, name) ? mocks[name] : require(name),
  }, { filename: path });
  return module.exports;
}

function makeHook() {
  const clients = [];
  const earlyChunk = new ArrayBuffer(8);
  class VoiceWSClient {
    constructor() { this.handlers = []; clients.push(this); }
    onMessage() {}
    onBinary(handler) { this.handlers.push(handler); }
    async connect() { this.handlers.forEach(handler => handler(earlyChunk)); }
    disconnect() { this.disconnected = true; }
  }
  const { useWebSocket } = loadSource('../src/hooks/useWebSocket.ts', {
    react: {
      useRef: current => ({ current }),
      useCallback: callback => callback,
      useEffect: () => {},
    },
    '../api/wsClient': { VoiceWSClient },
    '../stores/callStore': { useCallStore: { getState: () => ({}) } },
  });
  return { hook: useWebSocket(), clients, earlyChunk };
}

test('audio callback receives a chunk emitted before connect resolves', async () => {
  const { hook, earlyChunk } = makeHook();
  const received = [];
  await hook.connect('first', chunk => received.push(chunk));
  assert.deepEqual(received, [earlyChunk]);
});

test('repeated connect disconnects previous client and installs new audio callback', async () => {
  const { hook, clients, earlyChunk } = makeHook();
  const first = [], second = [];
  await hook.connect('first', chunk => first.push(chunk));
  await hook.connect('second', chunk => second.push(chunk));
  assert.equal(clients[0].disconnected, true);
  assert.deepEqual(first, [earlyChunk]);
  assert.deepEqual(second, [earlyChunk]);
});

test('connect remains compatible without callback and preserves onBinary registration', async () => {
  const { hook, clients } = makeHook();
  await hook.connect('legacy');
  const handler = () => {};
  hook.onBinary(handler);
  assert.equal(clients[0].handlers[0], handler);
  hook.disconnect();
  assert.equal(clients[0].disconnected, true);
});

test('sidebar links reflect the current route and preserve the current version', () => {
  const { Sidebar } = loadSource('../src/components/layout/Sidebar.tsx', {
    '../../stores/settingsStore': { useSettingsStore: () => ({ systemTitle: 'OmniVoice', systemSubtitle: 'Voice' }) },
  });
  for (const route of ['/call', '/agents', '/rag', '/skills', '/settings']) {
    const html = renderToStaticMarkup(React.createElement(MemoryRouter, { initialEntries: [route] }, React.createElement(Sidebar)));
    assert.match(html, new RegExp(`aria-current="page"[^>]*href="${route}"`));
    assert.match(html, /v0\.5\.0/);
    for (const link of ['/call', '/agents', '/rag', '/skills', '/settings']) {
      assert.ok(html.includes(`href="${link}"`));
    }
  }
});

test('each application route renders the expected panel', () => {
  const panels = {
    call: ['call/CallPanel', 'CallPanel'],
    agents: ['config/AgentConfig', 'AgentConfig'],
    rag: ['config/RAGManager', 'RAGManager'],
    skills: ['config/SkillManager', 'SkillManager'],
    settings: ['config/SettingsPanel', 'SettingsPanel'],
  };
  for (const [route, [, expected]] of Object.entries(panels)) {
    const mocks = {
      'react-router-dom': {
        ...require('react-router-dom'),
        BrowserRouter: ({ children }) => React.createElement(MemoryRouter, { initialEntries: [`/${route}`] }, children),
      },
      './stores/settingsStore': { useSettingsStore: selector => selector({ loaded: true, load: () => {} }) },
      './stores/agentStore': { useAgentStore: selector => selector({ load: () => {} }) },
      './components/layout/Sidebar': { Sidebar: () => null },
    };
    for (const [path, name] of Object.values(panels)) {
      mocks[`./components/${path}`] = { [name]: () => React.createElement('section', null, name) };
    }
    const { default: App } = loadSource('../src/App.tsx', mocks);
    assert.ok(renderToStaticMarkup(React.createElement(App)).includes(`<section>${expected}</section>`));
  }
});
