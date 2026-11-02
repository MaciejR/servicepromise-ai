import React from 'react';
import { createRoot } from 'react-dom/client';
import CatalogApp from './catalog/CatalogApp';
import LegacyApp from './LegacyApp';
createRoot(document.getElementById('root')!).render(<React.StrictMode>{new URLSearchParams(location.search).has('legacy')?<LegacyApp/>:<CatalogApp/>}</React.StrictMode>);
