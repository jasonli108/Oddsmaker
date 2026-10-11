import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { EventProvider } from './hooks/useEvent';
import { UserProvider } from './hooks/useUser';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <EventProvider>
        <UserProvider>
          <App />
        </UserProvider>
      </EventProvider>
    </BrowserRouter>
  </StrictMode>,
);
