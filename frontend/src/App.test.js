import { render, screen } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  global.fetch = jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
  );
  // jsdom does not implement scrollIntoView
  Element.prototype.scrollIntoView = jest.fn();
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
