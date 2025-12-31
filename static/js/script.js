let cartItems = [];

// Wrap all cart logic in DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
  const body = document.querySelector("body");
  const cartIcon = document.getElementById("cartIcon");
  const closeBtn = document.querySelector(".close");
  const cartItemCount = document.querySelector(".cart-item-count");
  const productList = document.querySelector(".productList");

  // Load cart from localStorage if exists
  cartItems = JSON.parse(localStorage.getItem("cart")) || [];

  cartIcon.addEventListener("click", () => {
    body.classList.toggle("active");
    renderCartItems();
  });

  closeBtn.addEventListener("click", () => {
    body.classList.remove("active");
  });

  // Search filter
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      const query = this.value.toLowerCase();
      const productCards = document.querySelectorAll(".product-card");
      productCards.forEach((card) => {
        const title = card.querySelector(".card-title").textContent.toLowerCase();
        card.parentElement.style.display = title.includes(query) ? "block" : "none";
      });
    });
  }

  const addToCartButtons = document.querySelectorAll(".add-to-cart");
  addToCartButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const productCard = btn.closest(".card");
      const name = productCard.querySelector(".card-title").innerText;
      const price = parseFloat(btn.dataset.price);
      const imageSrc = productCard.querySelector("img").getAttribute("src");

      const existing = cartItems.find((item) => item.name === name);
      if (existing) {
        existing.quantity += 1;
      } else {
        cartItems.push({ name, price, quantity: 1, imageSrc });
      }

      updateCartIcon();
      renderCartItems();
      updateCartDisplay();
      localStorage.setItem("cart", JSON.stringify(cartItems));
    });
  });

  function updateCartIcon() {
    const totalCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);
    cartItemCount.textContent = totalCount;
  }

  function renderCartItems() {
    productList.innerHTML = "";
    let total = 0;

    cartItems.forEach((item, index) => {
      total += item.price * item.quantity;

      const li = document.createElement("li");
      li.className = "cart-item";

      li.innerHTML = `
        <div class="item-image"><img src="${item.imageSrc}" /></div>
        <div class="item-details">
          <h4>${item.name}</h4>
          <div class="item-price">₹${item.price.toFixed(2)}</div>
          <div class="quantity-controls">
            <button class="qty-btn decrease">−</button>
            <span>${item.quantity}</span>
            <button class="qty-btn increase">+</button>
          </div>
        </div>
        <div class="item-actions">
          <div class="item-total">₹${(item.price * item.quantity).toFixed(2)}</div>
          <button class="remove-btn" data-index="${index}">&times;</button>
        </div>
      `;

      productList.appendChild(li);

      li.querySelector(".increase").addEventListener("click", () => {
        item.quantity++;
        updateCartIcon();
        renderCartItems();
        updateCartDisplay();
        localStorage.setItem("cart", JSON.stringify(cartItems));
      });

      li.querySelector(".decrease").addEventListener("click", () => {
        if (item.quantity > 1) {
          item.quantity--;
        } else {
          cartItems.splice(index, 1);
        }
        updateCartIcon();
        renderCartItems();
        updateCartDisplay();
        localStorage.setItem("cart", JSON.stringify(cartItems));
      });

      // Remove item
      li.querySelector(".remove-btn").addEventListener("click", () => {
        cartItems.splice(index, 1);
        updateCartIcon();
        renderCartItems();
        updateCartDisplay();
        localStorage.setItem("cart", JSON.stringify(cartItems));
      });
    });

    const totalPriceEl = document.querySelector(".total-price");
    if (totalPriceEl) totalPriceEl.textContent = `₹${total.toFixed(2)}`;
  }

  emailjs.init("f6pxCztEt4C2IsD9X");

  const checkoutBtn = document.getElementById("checkout-btn");
  if (checkoutBtn) {
    checkoutBtn.addEventListener("click", () => {
      if (cartItems.length === 0) {
        alert("Your cart is empty!");
        return;
      }

      fetch("/add-to-cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items: cartItems.map((i) => ({
            title: i.name,
            price: i.price,
            quantity: i.quantity,
            image: i.imageSrc,
          })),
        }),
      })
        .then((response) => {
          if (response.status === 403) {
            alert("Please login to proceed to checkout.");
            window.location.href = "/login.html";
            return;
          }
          return response.json();
        })
        .then((data) => {
          if (data && data.status === "success") {
            localStorage.removeItem("cart");
            alert("Cart saved! Redirecting to checkout...");
            window.location.href = "/checkout";
          }
        })
        .catch((err) => console.error(err));
    });
  }

  renderCartItems();
  updateCartIcon();
  updateCartDisplay();
});

function sendMail(event) {
  event.preventDefault();

  let parms = {
    name: document.getElementById("name").value,
    email: document.getElementById("email").value,
    message: document.getElementById("message").value,
  };

  emailjs
    .send("service_c9hxvdd", "template_okj94mk", parms)
    .then((response) => {
      alert("Email Sent Successfully!");
      document.getElementById("contactForm").reset();
      console.log("SUCCESS", response.status, response.text);
    })
    .catch((error) => {
      alert("Email Failed: " + error.text);
      console.error("FAILED...", error);
    });
}

function updateCartDisplay() {
  const totalAmountEl = document.getElementById("total-amount");
  const totalItemsEl = document.getElementById("total-items");
  let total = 0;
  let count = 0;

  cartItems.forEach((item) => {
    total += item.price * item.quantity;
    count += item.quantity;
  });

  if (totalAmountEl) totalAmountEl.textContent = total.toFixed(2);
  if (totalItemsEl) totalItemsEl.textContent = count;
}
