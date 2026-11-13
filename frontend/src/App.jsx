import React, { useState, useEffect } from "react";
import "./App.css";
import Login from "./pages/Login";
import Products from "./pages/Products";
import ProductReviews from "./pages/ProductReviews";
import Register from "./pages/Register";
import Index from "./pages/Index";

function App() {
  const [user, setUser] = useState(
    JSON.parse(localStorage.getItem("user")) || null
  );

  const [currentPage, setCurrentPage] = useState("home"); // "home" | "products" | "reviews"
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showRegister, setShowRegister] = useState(false);

  const [theme, setTheme] = useState(localStorage.getItem("theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () =>
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));

  const handleLogin = (loggedInUser) => {
    setUser(loggedInUser);
    localStorage.setItem("user", JSON.stringify(loggedInUser));
    setCurrentPage("home"); // Redirect to Index/Home page after login!
  };

  const handleLogout = () => {
    localStorage.removeItem("user");
    setUser(null);
    setSelectedProduct(null);
    setCurrentPage("home");
  };

  if (!user) {
    if (showRegister) {
      return (
        <Register
          onRegister={() => setShowRegister(false)}
          onBackToLogin={() => setShowRegister(false)}
          theme={theme}
          toggleTheme={toggleTheme}
        />
      );
    }

    return (
      <Login
        onLogin={handleLogin}
        onRegister={() => setShowRegister(true)}
        theme={theme}
        toggleTheme={toggleTheme}
      />
    );
  }

  // 1. Product Reviews page
  if (currentPage === "reviews" && selectedProduct) {
    return (
      <ProductReviews
        product={selectedProduct}
        onBack={() => setCurrentPage("products")}
        onNavigateHome={() => setCurrentPage("home")}
        theme={theme}
        toggleTheme={toggleTheme}
      />
    );
  }

  // 2. Full Products Catalog page
  if (currentPage === "products") {
    return (
      <Products
        user={user}
        onSelectProduct={(product) => {
          setSelectedProduct(product);
          setCurrentPage("reviews");
        }}
        onNavigateHome={() => setCurrentPage("home")}
        onLogout={handleLogout}
        theme={theme}
        toggleTheme={toggleTheme}
      />
    );
  }

  // 3. Default: Index / Home page
  return (
    <Index
      user={user}
      onNavigateToProducts={() => setCurrentPage("products")}
      onSelectProduct={(product) => {
        setSelectedProduct(product);
        setCurrentPage("reviews");
      }}
      onLogout={handleLogout}
      theme={theme}
      toggleTheme={toggleTheme}
    />
  );
}

export default App;