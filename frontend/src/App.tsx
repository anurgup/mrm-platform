import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import Container from "@mui/material/Container";
import { theme } from "./theme";
import { Navbar } from "./components/Navbar";
import { ModelList } from "./pages/ModelList";
import { ModelDetail } from "./pages/ModelDetail";

const queryClient = new QueryClient();

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Navbar />
          <Container maxWidth="lg" sx={{ py: 4 }}>
            <Routes>
              <Route path="/" element={<ModelList />} />
              <Route path="/models/:id" element={<ModelDetail />} />
            </Routes>
          </Container>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
