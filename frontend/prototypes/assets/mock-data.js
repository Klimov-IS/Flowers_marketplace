// Mock data for B2B Flower Marketplace prototypes
// This file contains hardcoded test data for all pages

const MOCK_DATA = {
  // Product catalog data
  products: [
    {
      id: "1",
      name: "Роза Красная 40 см",
      supplier: "База №1",
      supplier_id: "s1",
      price: 120,
      currency: "RUB",
      unit: "шт",
      stock: 180,
      length_cm: 40,
      product_type: "rose",
      color: "red",
      image: "assets/images/placeholder.svg",
      distance_km: 5.2,
      delivery_time_min: 15
    },
    {
      id: "2",
      name: "Тюльпаны Желтый 30 см",
      supplier: "База №1",
      supplier_id: "s1",
      price: 45,
      currency: "RUB",
      unit: "шт",
      stock: 80,
      length_cm: 30,
      product_type: "tulip",
      color: "yellow",
      image: "assets/images/placeholder.svg",
      distance_km: 5.2,
      delivery_time_min: 22
    },
    {
      id: "3",
      name: "Хризантема Белая 60 см",
      supplier: "База №1",
      supplier_id: "s1",
      price: 85,
      currency: "RUB",
      unit: "шт",
      stock: 200,
      length_cm: 60,
      product_type: "chrysanthemum",
      color: "white",
      image: "assets/images/placeholder.svg",
      distance_km: 5.2,
      delivery_time_min: 15
    },
    {
      id: "4",
      name: "Роза Белая 60 см",
      supplier: "База №1",
      supplier_id: "s1",
      price: 135,
      currency: "RUB",
      unit: "шт",
      stock: 150,
      length_cm: 60,
      product_type: "rose",
      color: "white",
      image: "assets/images/placeholder.svg",
      distance_km: 5.2,
      delivery_time_min: 15
    },
    {
      id: "5",
      name: "Пион Розовый 40 см",
      supplier: "База №2",
      supplier_id: "s2",
      price: 180,
      currency: "RUB",
      unit: "шт",
      stock: 45,
      length_cm: 40,
      product_type: "peony",
      color: "pink",
      image: "assets/images/placeholder.svg",
      distance_km: 8.7,
      delivery_time_min: 28
    },
    {
      id: "6",
      name: "Гортензия Синяя 60 см",
      supplier: "База №2",
      supplier_id: "s2",
      price: 220,
      currency: "RUB",
      unit: "шт",
      stock: 60,
      length_cm: 60,
      product_type: "hydrangea",
      color: "blue",
      image: "assets/images/placeholder.svg",
      distance_km: 8.7,
      delivery_time_min: 28
    },
    {
      id: "7",
      name: "Роза Розовая 40 см",
      supplier: "База №2",
      supplier_id: "s2",
      price: 125,
      currency: "RUB",
      unit: "шт",
      stock: 180,
      length_cm: 40,
      product_type: "rose",
      color: "pink",
      image: "assets/images/placeholder.svg",
      distance_km: 8.7,
      delivery_time_min: 22
    },
    {
      id: "8",
      name: "Тюльпаны Красный 40 см",
      supplier: "База №2",
      supplier_id: "s2",
      price: 50,
      currency: "RUB",
      unit: "шт",
      stock: 95,
      length_cm: 40,
      product_type: "tulip",
      color: "red",
      image: "assets/images/placeholder.svg",
      distance_km: 8.7,
      delivery_time_min: 22
    },
    {
      id: "9",
      name: "Лилия Белая 50 см",
      supplier: "База №3",
      supplier_id: "s3",
      price: 160,
      currency: "RUB",
      unit: "шт",
      stock: 70,
      length_cm: 50,
      product_type: "lily",
      color: "white",
      image: "assets/images/placeholder.svg",
      distance_km: 12.3,
      delivery_time_min: 38
    },
    {
      id: "10",
      name: "Хризантема Желтая 40 см",
      supplier: "База №3",
      supplier_id: "s3",
      price: 90,
      currency: "RUB",
      unit: "шт",
      stock: 175,
      length_cm: 40,
      product_type: "chrysanthemum",
      color: "yellow",
      image: "assets/images/placeholder.svg",
      distance_km: 12.3,
      delivery_time_min: 38
    },
    {
      id: "11",
      name: "Роза Желтая 50 см",
      supplier: "База №3",
      supplier_id: "s3",
      price: 140,
      currency: "RUB",
      unit: "шт",
      stock: 110,
      length_cm: 50,
      product_type: "rose",
      color: "yellow",
      image: "assets/images/placeholder.svg",
      distance_km: 12.3,
      delivery_time_min: 38
    },
    {
      id: "12",
      name: "Пион Белый 50 см",
      supplier: "База №3",
      supplier_id: "s3",
      price: 195,
      currency: "RUB",
      unit: "шт",
      stock: 30,
      length_cm: 50,
      product_type: "peony",
      color: "white",
      image: "assets/images/placeholder.svg",
      distance_km: 12.3,
      delivery_time_min: 38
    },
    {
      id: "13",
      name: "Гортензия Белая 50 см",
      supplier: "База №1",
      supplier_id: "s1",
      price: 210,
      currency: "RUB",
      unit: "шт",
      stock: 45,
      length_cm: 50,
      product_type: "hydrangea",
      color: "white",
      image: "assets/images/placeholder.svg",
      distance_km: 5.2,
      delivery_time_min: 15
    }
  ],

  // Shopping cart (buyer cabinet)
  cart: {
    items: [
      {
        supplier_id: "s1",
        supplier_name: "База №1",
        distance_km: 5.2,
        delivery_time_min: 15,
        items: [
          {
            id: "1",
            product_id: "1",
            name: "Роза Красная 40 см",
            price: 120,
            quantity: 50,
            stock: 180,
            image: "assets/images/placeholder.svg"
          },
          {
            id: "2",
            product_id: "3",
            name: "Хризантема Белая 60 см",
            price: 85,
            quantity: 30,
            stock: 200,
            image: "assets/images/placeholder.svg"
          }
        ]
      },
      {
        supplier_id: "s2",
        supplier_name: "База №2",
        distance_km: 8.7,
        delivery_time_min: 22,
        has_promo: true,
        promo_text: "Для магазинов из России работает беспроцентная рассрочка на товар! При заказе от 9 000 ₽ рассрочка на 6 месяцев.",
        promo_amount: 9000,
        items: [
          {
            id: "3",
            product_id: "8",
            name: "Тюльпаны Желтый 30 см",
            price: 45,
            quantity: 20,
            stock: 80,
            image: "assets/images/placeholder.svg"
          }
        ]
      }
    ]
  },

  // Order history (buyer cabinet)
  orders: [
    {
      id: "1234",
      order_number: "#1234",
      supplier: {
        id: "s1",
        name: "База №1"
      },
      status: "pending",
      status_text: "В обработке",
      date: "15.01.2024, 14:30",
      total: 8550,
      currency: "RUB",
      phone: "ТЕЛ: 1234-5678",
      timeline: [
        {
          status: "created",
          label: "Заказ принят",
          completed: true,
          datetime: "14.01.2024, 14:30"
        },
        {
          status: "processing",
          label: "Сборка заказа",
          completed: true,
          datetime: "14.01.2024, 16:45"
        },
        {
          status: "in_transit",
          label: "В пути",
          completed: false,
          current: true,
          expected: "15.01.2024, 17:00"
        },
        {
          status: "delivered",
          label: "Доставлен",
          completed: false,
          expected: "Ожидается"
        }
      ],
      delivery: {
        distance_km: 5.2,
        time_min: 18,
        message: "Заказ в пути у вас"
      }
    },
    {
      id: "1233",
      order_number: "#1233",
      supplier: {
        id: "s2",
        name: "База №2"
      },
      status: "completed",
      status_text: "Выполнен",
      date: "14.01.2024, 10:15",
      total: 2260,
      currency: "RUB",
      phone: "ТЕЛ: 1233-3678"
    },
    {
      id: "1232",
      order_number: "#1232",
      supplier: {
        id: "s1",
        name: "База №1"
      },
      status: "completed",
      status_text: "Выполнен",
      date: "13.01.2024, 16:45",
      total: 5100,
      currency: "RUB",
      phone: "ТЕЛ: 1232-3434"
    }
  ],

  // Buyer statistics
  buyerStats: {
    total_spent: 9450,
    savings: 0,
    orders_count: 2
  },

  // Seller statistics
  sellerStats: {
    products_in_catalog: 156,
    pending_review: 12,
    active_orders: 3
  },

  // Normalization errors (seller cabinet)
  normalizationErrors: [
    {
      id: "n1",
      supplier_item: "Rose Yel. 40cm",
      normalized_sku_id: null,
      options: [
        { id: "sku1", label: "Роза Желтая 40 см" },
        { id: "sku2", label: "Роза Розовая 40 см" },
        { id: "sku3", label: "Роза Белая 40 см" }
      ]
    },
    {
      id: "n2",
      supplier_item: "Tulip Red 30",
      normalized_sku_id: null,
      options: [
        { id: "sku4", label: "Тюльпаны Красный 30 см" },
        { id: "sku5", label: "Тюльпаны Желтый 30 см" },
        { id: "sku6", label: "Тюльпаны Розовый 30 см" }
      ]
    }
  ],

  // Stock updates (seller cabinet)
  stockUpdates: [
    {
      id: "1",
      product: "Роза Красная 40 см",
      current_stock: 180
    },
    {
      id: "3",
      product: "Тюльпаны Желтый 30 см",
      current_stock: 80
    }
  ],

  // Incoming orders (seller cabinet)
  incomingOrders: [
    {
      id: "1234",
      order_number: "#1234",
      buyer: "Retail Shop A",
      date: "15.01.2024, 14:30",
      total: 8550,
      currency: "RUB",
      status: "pending",
      status_text: "В обработке"
    },
    {
      id: "1235",
      order_number: "#1235",
      buyer: "Flower Market B",
      date: "15.01.2024, 12:15",
      total: 12300,
      currency: "RUB",
      status: "pending",
      status_text: "В обработке"
    },
    {
      id: "1236",
      order_number: "#1236",
      buyer: "Boutique C",
      date: "15.01.2024, 09:45",
      total: 5670,
      currency: "RUB",
      status: "confirmed",
      status_text: "Подтвержден"
    }
  ]
};

// Helper functions
const MockDataHelpers = {
  // Get products by type
  getProductsByType(type) {
    if (!type || type === 'all') return MOCK_DATA.products;
    return MOCK_DATA.products.filter(p => p.product_type === type);
  },

  // Filter products
  filterProducts(filters) {
    let results = [...MOCK_DATA.products];

    if (filters.type && filters.type !== 'all') {
      results = results.filter(p => p.product_type === filters.type);
    }

    if (filters.priceMin) {
      results = results.filter(p => p.price >= filters.priceMin);
    }

    if (filters.priceMax) {
      results = results.filter(p => p.price <= filters.priceMax);
    }

    if (filters.length && filters.length.length > 0) {
      results = results.filter(p => filters.length.includes(p.length_cm));
    }

    if (filters.color && filters.color.length > 0) {
      results = results.filter(p => filters.color.includes(p.color));
    }

    if (filters.search) {
      const search = filters.search.toLowerCase();
      results = results.filter(p =>
        p.name.toLowerCase().includes(search) ||
        p.supplier.toLowerCase().includes(search)
      );
    }

    return results;
  },

  // Sort products
  sortProducts(products, sortBy) {
    const sorted = [...products];
    switch (sortBy) {
      case 'price_asc':
        return sorted.sort((a, b) => a.price - b.price);
      case 'price_desc':
        return sorted.sort((a, b) => b.price - a.price);
      case 'name_asc':
        return sorted.sort((a, b) => a.name.localeCompare(b.name));
      default:
        return sorted;
    }
  },

  // Calculate cart total
  calculateCartTotal(supplierCart) {
    return supplierCart.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  },

  // Calculate grand total
  calculateGrandTotal() {
    return MOCK_DATA.cart.items.reduce((sum, supplier) => {
      return sum + this.calculateCartTotal(supplier);
    }, 0);
  },

  // Get cart item count
  getCartItemCount() {
    return MOCK_DATA.cart.items.reduce((sum, supplier) => {
      return sum + supplier.items.reduce((s, item) => s + item.quantity, 0);
    }, 0);
  }
};

// Make available globally
window.MOCK_DATA = MOCK_DATA;
window.MockDataHelpers = MockDataHelpers;
