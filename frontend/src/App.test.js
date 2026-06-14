import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';

function mockFetchOnce(impl) {
  global.fetch.mockImplementationOnce(impl);
}

beforeEach(() => {
  // Default: home/stats call returns empty stats.
  global.fetch = jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve({ docs_indexed: 0, total_chunks: 0 }) })
  );
  Element.prototype.scrollIntoView = jest.fn();
  window.localStorage.clear();
});

afterEach(() => {
  jest.resetAllMocks();
});

test('renders the hybrid RAG welcome message', () => {
  render(<App />);
  expect(
    screen.getByText(/upload your pdf documents using the sidebar/i)
  ).toBeInTheDocument();
});

test('sends the session id header on the initial health call', async () => {
  render(<App />);
  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  const [, options] = global.fetch.mock.calls[0];
  expect(options.headers['X-Session-ID']).toBeTruthy();
});

test('shows backend ready badge when health check succeeds', async () => {
  render(<App />);
  expect(await screen.findByText(/backend ready/i)).toBeInTheDocument();
});

test('shows offline banner when the backend is unreachable', async () => {
  global.fetch = jest.fn(() => Promise.reject(new Error('network down')));
  render(<App />);
  expect(await screen.findByText(/backend not running/i)).toBeInTheDocument();
});

test('submitting a question renders the answer and sources', async () => {
  render(<App />);
  await waitFor(() => expect(screen.getByText(/backend ready/i)).toBeInTheDocument());

  mockFetchOnce(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        answer: 'The capital is Paris.',
        sources: [{ doc: 'geo.pdf', page: 2, snippet: 'Paris is the capital.' }],
      }),
    })
  );

  const textarea = screen.getByPlaceholderText(/ask/i);
  fireEvent.change(textarea, { target: { value: 'What is the capital?' } });
  fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

  expect(await screen.findByText(/the capital is paris/i)).toBeInTheDocument();
  expect(await screen.findByText(/geo\.pdf/i)).toBeInTheDocument();

  const queryCall = global.fetch.mock.calls.find(([url]) => url.endsWith('/query'));
  expect(queryCall[1].headers['X-Session-ID']).toBeTruthy();
});

test('clear session button calls DELETE /session', async () => {
  render(<App />);
  await waitFor(() => expect(screen.getByText(/backend ready/i)).toBeInTheDocument());

  mockFetchOnce(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));

  fireEvent.click(screen.getByText(/clear session/i));

  await waitFor(() => {
    const deleteCall = global.fetch.mock.calls.find(
      ([url, opts]) => url.endsWith('/session') && opts.method === 'DELETE'
    );
    expect(deleteCall).toBeTruthy();
  });
  expect(await screen.findByText(/session cleared/i)).toBeInTheDocument();
});
