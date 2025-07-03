import React, { useState, useEffect, createContext, useContext, useRef } from 'react';
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } from 'firebase/auth';
import { getFirestore, doc, getDoc, setDoc, updateDoc, onSnapshot, collection, query, addDoc, deleteDoc, getDocs } from 'firebase/firestore';

// Context for Firebase and User
const AppContext = createContext(null);

const App = () => {
    const [db, setDb] = useState(null);
    const [auth, setAuth] = useState(null);
    const [userId, setUserId] = useState(null);
    const [userRole, setUserRole] = useState(null); // 'admin' or 'buyer'
    const [userEmail, setUserEmail] = useState(null); // Store the email entered during login
    const [isAuthReady, setIsAuthReady] = useState(false);
    const [showLoginModal, setShowLoginModal] = useState(true); // Show login modal initially

    // Firebase Initialization and Auth Listener
    useEffect(() => {
        const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
        const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : {};

        try {
            const app = initializeApp(firebaseConfig);
            const firestoreDb = getFirestore(app);
            const firebaseAuth = getAuth(app);

            setDb(firestoreDb);
            setAuth(firebaseAuth);

            const unsubscribe = onAuthStateChanged(firebaseAuth, async (user) => {
                if (user) {
                    setUserId(user.uid);
                    // IMPORTANT: We are no longer persisting user role/email in Firestore on login.
                    // So, we don't try to fetch it here.
                    // The role and email will be set by the LoginModal for the current session.
                    setUserRole(null); // Ensure role is null until explicitly set by login modal
                    setUserEmail(null); // Ensure email is null until explicitly set by login modal
                    setIsAuthReady(true);
                    setShowLoginModal(true); // Always show login modal to re-select role/email for this session
                } else {
                    setUserId(null);
                    setUserRole(null);
                    setUserEmail(null);
                    setShowLoginModal(true);
                    setIsAuthReady(true);

                    // Attempt to sign in anonymously if no user is present.
                    // This ensures a Firebase UID is always available for the login modal to attach profile to.
                    try {
                        if (typeof __initial_auth_token !== 'undefined' && __initial_auth_token) {
                            await signInWithCustomToken(firebaseAuth, __initial_auth_token);
                        } else {
                            await signInAnonymously(firebaseAuth);
                        }
                        console.log("Signed in anonymously or with custom token.");
                    } catch (anonError) {
                        console.error("Error during anonymous sign-in or custom token sign-in:", anonError);
                    }
                }
            });

            return () => unsubscribe();
        } catch (error) {
            console.error("Error initializing Firebase:", error);
        }
    }, []); // Empty dependency array means this runs once on mount

    // Effect to seed initial products if the collection is empty
    useEffect(() => {
        const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
        const seedInitialProducts = async () => {
            if (!db) return;

            const productsColRef = collection(db, `artifacts/${appId}/public/data/products`);
            try {
                const existingProducts = await getDocs(productsColRef);
                if (existingProducts.empty) {
                    console.log("No products found, adding initial products...");
                    await addDoc(productsColRef, { name: "Galleta", price: 800, quantity: 100 });
                    await addDoc(productsColRef, { name: "Bebida", price: 1000, quantity: 200 });
                    await addDoc(productsColRef, { name: "Empanada", price: 2800, quantity: 300 });
                    await addDoc(productsColRef, { name: "almuerzo", price: 3300, quantity: 150 });
                    console.log("Initial products added successfully.");
                } else {
                    console.log("Products already exist, skipping initial seeding.");
                }
            } catch (error) {
                console.error("Error seeding initial products:", error);
            }
        };

        if (db && isAuthReady) { // Ensure db is initialized and auth state is ready
            seedInitialProducts();
        }
    }, [db, isAuthReady]);


    // Effect to hide login modal once role and email are set
    useEffect(() => {
        if (isAuthReady && userId && userRole && userEmail) {
            setShowLoginModal(false);
        } else if (isAuthReady && userId && (!userRole || !userEmail)) {
            // If authenticated but role/email not set, show login modal to set them
            setShowLoginModal(true);
        }
    }, [isAuthReady, userId, userRole, userEmail]);

    // This function is called from LoginModal after successful validation
    const handleLoginAttempt = async (role, email) => {
        // We no longer save role and email to Firestore here.
        // They are only set in the component's state for the current session.
        setUserRole(role);
        setUserEmail(email);
        setShowLoginModal(false);
        console.log(`User logged in: Role - ${role}, Email - ${email}`);
    };

    const handleLogout = async () => { // Made async
        if (auth) {
            try {
                await auth.signOut(); // Sign out the current Firebase user
                console.log("Firebase user signed out.");
                // onAuthStateChanged listener will now detect null user and trigger new anonymous sign-in
            } catch (error) {
                console.error("Error signing out Firebase user:", error);
            }
        }
        // Reset app-specific states immediately after signOut attempt
        setUserId(null);
        setUserRole(null);
        setUserEmail(null);
        setShowLoginModal(true); // Show the login modal again
    };

    if (!isAuthReady) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-100">
                <p className="text-xl text-gray-700">Cargando aplicación...</p>
            </div>
        );
    }

    return (
        <AppContext.Provider value={{ db, auth, userId, userRole, userEmail, setUserRole, setUserEmail, handleLogout }}>
            <div className="min-h-screen bg-gray-100 font-inter">
                {showLoginModal && (
                    <LoginModal onLogin={handleLoginAttempt} />
                )}
                {!showLoginModal && (
                    <div className="container mx-auto p-4">
                        <h1 className="text-4xl font-bold text-center text-gray-800 mb-8 rounded-lg p-4 bg-white shadow-md">
                            Casino Universitario
                        </h1>
                        <p className="text-center text-gray-600 mb-6">
                            ID de Usuario: <span className="font-mono bg-gray-200 px-2 py-1 rounded-md text-sm">{userId}</span>
                            <br />
                            Email: <span className="font-mono bg-gray-200 px-2 py-1 rounded-md text-sm">{userEmail}</span>
                        </p>
                        {userRole === 'admin' && <AdminDashboard />}
                        {userRole === 'buyer' && <BuyerDashboard />}
                    </div>
                )}
            </div>
        </AppContext.Provider>
    );
};

const LoginModal = ({ onLogin }) => {
    // Initialize email state without localStorage
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [errorMessage, setErrorMessage] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        setErrorMessage(''); // Clear previous errors

        if (email === 'admin123@gmail.com') {
            // Admin login: specific email, password must be '123456'
            if (password === '123456') {
                onLogin('admin', email);
            } else {
                setErrorMessage('Contraseña incorrecta para el administrador.');
            }
        } else if (email.endsWith('@usm.cl')) {
            // Buyer login: @usm.cl domain, password is not checked
            onLogin('buyer', email);
        } else {
            setErrorMessage('Dominio de correo no permitido. Use @usm.cl o admin123@gmail.com.');
        }
    };

    return (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-white p-8 rounded-lg shadow-xl max-w-md w-full">
                <h2 className="text-3xl font-bold text-center text-gray-800 mb-6">Iniciar Sesión</h2>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label htmlFor="email" className="block text-lg font-medium text-gray-700 mb-2">
                            Correo Electrónico:
                        </label>
                        <input
                            type="email"
                            id="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="mt-1 block w-full pl-3 pr-3 py-3 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-lg rounded-md shadow-sm"
                            placeholder="tu_correo@usm.cl"
                            required
                        />
                    </div>
                    {/* Password field only appears if the email is 'admin123@gmail.com' */}
                    {email === 'admin123@gmail.com' && (
                        <div>
                            <label htmlFor="password" className="block text-lg font-medium text-gray-700 mb-2">
                                Contraseña:
                            </label>
                            <input
                                type="password"
                                id="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="mt-1 block w-full pl-3 pr-3 py-3 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-lg rounded-md shadow-sm"
                                placeholder="Contraseña"
                                required // Password is required for admin email
                            />
                        </div>
                    )}
                    {errorMessage && (
                        <p className="text-red-600 text-center text-sm">{errorMessage}</p>
                    )}
                    <button
                        type="submit"
                        // Button is enabled if:
                        // 1. Email is provided AND
                        // 2. (If email is admin, password must be provided) OR (If email is buyer, password is not strictly needed for button enable)
                        disabled={!email || (email === 'admin123@gmail.com' && !password)}
                        className={`w-full py-3 px-4 border border-transparent rounded-md shadow-sm text-lg font-medium text-white ${
                            (email && (password || email.endsWith('@usm.cl'))) ? 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500' : 'bg-gray-400 cursor-not-allowed'
                        }`}
                    >
                        Entrar
                    </button>
                </form>
            </div>
        </div>
    );
};

const ProductCard = ({ product, isAdmin, onUpdateQuantity, onAddToCart }) => {
    const [editQuantity, setEditQuantity] = useState(product.quantity);
    const [selectedQuantity, setSelectedQuantity] = useState(1); // New state for buyer's selected quantity
    const [stockError, setStockError] = useState(''); // New state for stock error message

    const handleSaveQuantity = () => {
        onUpdateQuantity(product.id, editQuantity);
    };

    const handleAddToCartClick = () => {
        if (selectedQuantity > 0) {
            // Check if selected quantity exceeds available stock
            if (selectedQuantity > product.quantity) {
                setStockError('No hay suficiente stock');
                setTimeout(() => setStockError(''), 3000); // Clear error after 3 seconds
            } else {
                setStockError(''); // Clear any previous error
                onAddToCart(product, selectedQuantity); // Pass selectedQuantity
                setSelectedQuantity(1); // Reset selected quantity after adding to cart
            }
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-md p-6 flex flex-col justify-between h-full">
            <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{product.name}</h3>
                <p className="text-gray-700 mb-4">Precio: ${product.price}</p>
                {isAdmin ? (
                    <div className="mb-4">
                        <label htmlFor={`quantity-${product.id}`} className="block text-sm font-medium text-gray-700 mb-1">
                            Cantidad Disponible:
                        </label>
                        <div className="flex items-center space-x-2">
                            <input
                                type="number"
                                id={`quantity-${product.id}`}
                                value={editQuantity}
                                onChange={(e) => setEditQuantity(parseInt(e.target.value) || 0)}
                                min="0"
                                className="w-24 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            />
                            <button
                                onClick={handleSaveQuantity}
                                className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded-md shadow-sm transition duration-150 ease-in-out"
                            >
                                Guardar
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="mb-4">
                        <p className="text-gray-700 mb-2">Cantidad Disponible: {product.quantity}</p>
                        <label htmlFor={`select-quantity-${product.id}`} className="block text-sm font-medium text-gray-700 mb-1">
                            Cantidad a comprar:
                        </label>
                        <input
                            type="number"
                            id={`select-quantity-${product.id}`}
                            value={selectedQuantity}
                            onChange={(e) => setSelectedQuantity(parseInt(e.target.value) || 1)}
                            min="1"
                            max={product.quantity} // Max quantity is available stock
                            className="w-24 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                        {stockError && (
                            <p className="text-red-500 text-sm mt-1">{stockError}</p>
                        )}
                    </div>
                )}
            </div>
            {!isAdmin && (
                <button
                    onClick={handleAddToCartClick}
                    disabled={product.quantity === 0 || selectedQuantity <= 0 || selectedQuantity > product.quantity}
                    className={`mt-4 w-full py-2 px-4 rounded-md font-semibold transition duration-150 ease-in-out ${
                        product.quantity > 0 && selectedQuantity > 0 && selectedQuantity <= product.quantity ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-md' : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    }`}
                >
                    {product.quantity > 0 ? 'Agregar al Carrito' : 'Agotado'}
                </button>
            )}
        </div>
    );
};

const ProductList = ({ isAdmin }) => {
    const { db, userId } = useContext(AppContext);
    const [products, setProducts] = useState([]);
    const [cart, setCart] = useState({}); // {productId: quantity}
    const [showCartModal, setShowCartModal] = useState(false);
    const [message, setMessage] = useState('');
    const messageTimeoutRef = useRef(null);

    const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

    // Fetch products and listen for real-time updates
    useEffect(() => {
        if (!db) return;

        const productsColRef = collection(db, `artifacts/${appId}/public/data/products`);
        const unsubscribe = onSnapshot(productsColRef, (snapshot) => {
            const productsData = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
            setProducts(productsData);
        }, (error) => {
            console.error("Error fetching products:", error);
        });

        return () => unsubscribe();
    }, [db, appId]);

    // Fetch user's cart
    useEffect(() => {
        if (!db || !userId || isAdmin) return;

        const cartDocRef = doc(db, `artifacts/${appId}/users/${userId}/cart/current_cart`);
        const unsubscribe = onSnapshot(cartDocRef, (docSnap) => {
            if (docSnap.exists()) {
                setCart(docSnap.data().items || {});
            } else {
                setCart({});
            }
        }, (error) => {
            console.error("Error fetching cart:", error);
        });

        return () => unsubscribe();
    }, [db, userId, isAdmin, appId]);

    const showTemporaryMessage = (msg, isError = false) => {
        setMessage(msg);
        if (messageTimeoutRef.current) {
            clearTimeout(messageTimeoutRef.current);
        }
        messageTimeoutRef.current = setTimeout(() => {
            setMessage('');
        }, 3000); // Message disappears after 3 seconds
    };

    const handleUpdateProductQuantity = async (productId, newQuantity) => {
        if (!db) return;
        const productDocRef = doc(db, `artifacts/${appId}/public/data/products`, productId);
        try {
            await updateDoc(productDocRef, { quantity: newQuantity });
            showTemporaryMessage(`Cantidad de ${products.find(p => p.id === productId)?.name} actualizada.`);
        } catch (error) {
            console.error("Error updating product quantity:", error);
            showTemporaryMessage("Error al actualizar la cantidad.");
        }
    };

    const handleAddToCart = async (product, quantityToAdd) => {
        if (!db || !userId) return;

        const currentCartQuantity = cart[product.id] || 0;
        const newTotalQuantityInCart = currentCartQuantity + quantityToAdd;

        // Check if adding this quantity would exceed available stock
        if (newTotalQuantityInCart > product.quantity) {
            showTemporaryMessage(`No hay suficiente stock para añadir ${quantityToAdd} de ${product.name}. Solo quedan ${product.quantity - currentCartQuantity} disponibles.`, true);
            return;
        }

        const newCart = { ...cart, [product.id]: newTotalQuantityInCart };
        const cartDocRef = doc(db, `artifacts/${appId}/users/${userId}/cart/current_cart`);
        try {
            await setDoc(cartDocRef, { items: newCart }, { merge: true });
            showTemporaryMessage(`${quantityToAdd} de ${product.name} agregado al carrito.`);
        } catch (error) {
            console.error("Error adding to cart:", error);
            showTemporaryMessage("Error al agregar al carrito.");
        }
    };

    const handleRemoveFromCart = async (product) => {
        if (!db || !userId) return;

        const currentCartQuantity = cart[product.id] || 0;
        if (currentCartQuantity <= 1) {
            const newCart = { ...cart };
            delete newCart[product.id];
            const cartDocRef = doc(db, `artifacts/${appId}/users/${userId}/cart/current_cart`);
            try {
                await setDoc(cartDocRef, { items: newCart }, { merge: true });
                showTemporaryMessage(`${product.name} eliminado del carrito.`);
            } catch (error) {
                console.error("Error removing from cart:", error);
                showTemporaryMessage("Error al eliminar del carrito.");
            }
        } else {
            const newCart = { ...cart, [product.id]: currentCartQuantity - 1 };
            const cartDocRef = doc(db, `artifacts/${appId}/users/${userId}/cart/current_cart`);
            try {
                await setDoc(cartDocRef, { items: newCart }, { merge: true });
                showTemporaryMessage(`Cantidad de ${product.name} reducida.`);
            } catch (error) {
                console.error("Error reducing quantity in cart:", error);
                showTemporaryMessage("Error al reducir la cantidad en el carrito.");
            }
        }
    };

    const handleClearCart = async () => {
        if (!db || !userId) return;
        const cartDocRef = doc(db, `artifacts/${appId}/users/${userId}/cart/current_cart`);
        try {
            await setDoc(cartDocRef, { items: {} });
            setCart({});
            showTemporaryMessage("Carrito vaciado.");
        } catch (error) {
            console.error("Error clearing cart:", error);
            showTemporaryMessage("Error al vaciar el carrito.");
        }
    };

    const getCartItemsDetails = () => {
        return Object.entries(cart).map(([productId, quantity]) => {
            const product = products.find(p => p.id === productId);
            return product ? { ...product, cartQuantity: quantity } : null;
        }).filter(Boolean);
    };

    const totalCartPrice = getCartItemsDetails().reduce((sum, item) => sum + (item.price * item.cartQuantity), 0);

    return (
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-3xl font-bold text-gray-800 mb-6 text-center">
                {isAdmin ? 'Gestión de Productos' : 'Productos Disponibles'}
            </h2>
            {message && (
                <div className="fixed top-4 right-4 bg-blue-500 text-white px-4 py-2 rounded-md shadow-lg z-50">
                    {message}
                </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {products.map(product => (
                    <ProductCard
                        key={product.id}
                        product={product}
                        isAdmin={isAdmin}
                        onUpdateQuantity={handleUpdateProductQuantity}
                        onAddToCart={handleAddToCart}
                    />
                ))}
            </div>
            {!isAdmin && (
                <div className="mt-8 text-center">
                    <button
                        onClick={() => setShowCartModal(true)}
                        className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-6 rounded-lg shadow-lg transition duration-150 ease-in-out transform hover:scale-105"
                    >
                        Ver Carrito ({Object.values(cart).reduce((sum, qty) => sum + qty, 0)})
                    </button>
                </div>
            )}

            {showCartModal && (
                <CartModal
                    cartItems={getCartItemsDetails()}
                    totalPrice={totalCartPrice}
                    onClose={() => setShowCartModal(false)}
                    onRemove={handleRemoveFromCart}
                    onClear={handleClearCart}
                />
            )}
        </div>
    );
};

const CartModal = ({ cartItems, totalPrice, onClose, onRemove, onClear }) => {
    const { db, userId } = useContext(AppContext);
    const [isConfirmingOrder, setIsConfirmingOrder] = useState(false);
    const [orderMessage, setOrderMessage] = useState('');
    const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

    const handleConfirmOrder = async () => {
        if (!db || !userId || cartItems.length === 0) return;

        setIsConfirmingOrder(true);
        setOrderMessage('Confirmando tu pedido...');

        try {
            // 1. Create a new order document
            const ordersColRef = collection(db, `artifacts/${appId}/public/data/orders`);
            const newOrderRef = await addDoc(ordersColRef, {
                userId: userId,
                items: cartItems.map(item => ({
                    productId: item.id,
                    name: item.name,
                    price: item.price,
                    quantity: item.cartQuantity
                })),
                totalPrice: totalPrice,
                status: 'pending', // 'pending', 'ready_for_pickup', 'completed', 'cancelled'
                orderTime: new Date(),
                pickupTime: null,
                queuePosition: null // Will be set by queue manager
            });

            // 2. Add to virtual queue
            const queueColRef = collection(db, `artifacts/${appId}/public/data/queue`);
            await addDoc(queueColRef, {
                orderId: newOrderRef.id,
                userId: userId,
                status: 'waiting', // 'waiting', 'notified', 'missed', 'completed'
                timestamp: new Date(),
                pickupDeadline: null,
                notifiedAt: null
            });

            // 3. Clear the user's cart
            const cartDocRef = doc(db, `artifacts/${appId}/users/${userId}/cart/current_cart`);
            await setDoc(cartDocRef, { items: {} });

            setOrderMessage('¡Pedido confirmado! Serás redirigido a la fila virtual.');
            setTimeout(() => {
                onClose(); // Close cart modal
                // The BuyerDashboard will automatically switch to QueueView
            }, 2000);

        } catch (error) {
            console.error("Error confirming order:", error);
            setOrderMessage('Error al confirmar el pedido. Inténtalo de nuevo.');
            setIsConfirmingOrder(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-white p-8 rounded-lg shadow-xl max-w-2xl w-full">
                <h2 className="text-3xl font-bold text-center text-gray-800 mb-6 text-center">Tu Carrito</h2>
                {cartItems.length === 0 ? (
                    <p className="text-center text-gray-600 text-lg">Tu carrito está vacío.</p>
                ) : (
                    <>
                        <ul className="space-y-4 mb-6 max-h-80 overflow-y-auto">
                            {cartItems.map(item => (
                                <li key={item.id} className="flex justify-between items-center bg-gray-50 p-4 rounded-md shadow-sm">
                                    <div>
                                        <p className="text-lg font-medium text-gray-900">{item.name}</p>
                                        {/* Display item price without decimals */}
                                        <p className="text-gray-600 text-sm">
                                            ${item.price} x {item.cartQuantity}
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => onRemove(item)}
                                        className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-md shadow-sm transition duration-150 ease-in-out"
                                    >
                                        Quitar
                                    </button>
                                </li>
                            ))}
                        </ul>
                        <div className="border-t border-gray-200 pt-4 mt-4 flex justify-between items-center">
                            {/* Display total price without decimals */}
                            <p className="text-xl font-bold text-gray-800">Total: ${totalPrice}</p>
                            <button
                                onClick={onClear}
                                className="bg-yellow-500 hover:bg-yellow-600 text-white font-bold py-2 px-4 rounded-md shadow-sm transition duration-150 ease-in-out"
                            >
                                Vaciar Carrito
                            </button>
                        </div>
                        <div className="mt-8 flex justify-end space-x-4">
                            <button
                                onClick={onClose}
                                className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-3 px-6 rounded-lg shadow-md transition duration-150 ease-in-out"
                            >
                                Seguir Comprando
                            </button>
                            <button
                                onClick={handleConfirmOrder}
                                disabled={isConfirmingOrder || cartItems.length === 0}
                                className={`py-3 px-6 rounded-lg font-bold text-white shadow-lg transition duration-150 ease-in-out transform hover:scale-105 ${
                                    isConfirmingOrder || cartItems.length === 0 ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'
                                }`}
                            >
                                {isConfirmingOrder ? 'Procesando...' : 'Confirmar Pedido'}
                            </button>
                        </div>
                    </>
                )}
                {orderMessage && (
                    <p className="mt-4 text-center text-lg font-semibold text-blue-600">{orderMessage}</p>
                )}
            </div>
        </div>
    );
};

const BuyerDashboard = () => {
    const { db, userId, handleLogout } = useContext(AppContext); // Destructure handleLogout
    const [hasPendingOrder, setHasPendingOrder] = useState(false);
    const [currentQueueItem, setCurrentQueueItem] = useState(null);
    const [pickupCountdown, setPickupCountdown] = useState(null); // in seconds
    const countdownIntervalRef = useRef(null);
    const [showMessageModal, setShowMessageModal] = useState(false);
    const [messageContent, setMessageContent] = useState('');

    const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

    // Check for pending orders or queue status
    useEffect(() => {
        if (!db || !userId) return;

        const queueColRef = collection(db, `artifacts/${appId}/public/data/queue`);
        const q = query(queueColRef); // No 'where' clause initially, filter on client

        const unsubscribe = onSnapshot(q, (snapshot) => {
            let userHasPending = false;
            let userQueueItem = null;
            snapshot.docs.forEach(doc => {
                const item = { id: doc.id, ...doc.data() };
                if (item.userId === userId && (item.status === 'waiting' || item.status === 'notified')) {
                    userHasPending = true;
                    userQueueItem = item;
                }
            });
            setHasPendingOrder(userHasPending);
            setCurrentQueueItem(userQueueItem);

            if (userQueueItem && userQueueItem.status === 'notified') {
                const notifiedAt = userQueueItem.notifiedAt?.toDate();
                if (notifiedAt) {
                    const deadline = new Date(notifiedAt.getTime() + 5 * 60 * 1000); // 5 minutes from notification
                    const now = new Date();
                    const remaining = Math.max(0, Math.floor((deadline.getTime() - now.getTime()) / 1000));
                    setPickupCountdown(remaining);

                    // Clear previous interval if exists
                    if (countdownIntervalRef.current) {
                        clearInterval(countdownIntervalRef.current);
                    }

                    countdownIntervalRef.current = setInterval(() => {
                        const newNow = new Date();
                        const newRemaining = Math.max(0, Math.floor((deadline.getTime() - newNow.getTime()) / 1000));
                        setPickupCountdown(newRemaining);
                        if (newRemaining === 0) {
                            clearInterval(countdownIntervalRef.current);
                            // Optionally mark as missed if time runs out
                            if (userQueueItem.status === 'notified') {
                                handleMissedPickup(userQueueItem.id);
                            }
                        }
                    }, 1000);

                    // Show notification message
                    if (!showMessageModal) { // Only show if not already showing
                        setMessageContent('¡Es tu turno para recoger tu pedido! Tienes 5 minutos.');
                        setShowMessageModal(true);
                    }

                }
            } else {
                clearInterval(countdownIntervalRef.current);
                setPickupCountdown(null);
                setShowMessageModal(false); // Hide message if not notified
            }
        }, (error) => {
            console.error("Error fetching queue status:", error);
        });

        return () => {
            unsubscribe();
            if (countdownIntervalRef.current) {
                clearInterval(countdownIntervalRef.current);
            }
        };
    }, [db, userId, appId, showMessageModal]);

    const handleMissedPickup = async (queueItemId) => {
        if (!db) return;
        const queueItemRef = doc(db, `artifacts/${appId}/public/data/queue`, queueItemId);
        try {
            await updateDoc(queueItemRef, { status: 'missed' });
            setMessageContent('Tu tiempo para recoger el pedido ha expirado. Por favor, contacta al personal.');
            setShowMessageModal(true);
        } catch (error) {
            console.error("Error marking order as missed:", error);
        }
    };

    const formatTime = (seconds) => {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div>
            <div className="flex justify-end mb-4">
                <button
                    onClick={handleLogout}
                    className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-150 ease-in-out"
                >
                    Cerrar Sesión
                </button>
            </div>
            {hasPendingOrder && currentQueueItem ? (
                <QueueView
                    queueItem={currentQueueItem}
                    countdown={pickupCountdown}
                    onCloseMessage={() => setShowMessageModal(false)}
                    showMessageModal={showMessageModal}
                    messageContent={messageContent}
                />
            ) : (
                <ProductList isAdmin={false} />
            )}
        </div>
    );
};

const QueueView = ({ queueItem, countdown, onCloseMessage, showMessageModal, messageContent }) => {
    const { db, userId } = useContext(AppContext);
    const [queuePosition, setQueuePosition] = useState(null);
    const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

    useEffect(() => {
        if (!db || !userId) return;

        const queueColRef = collection(db, `artifacts/${appId}/public/data/queue`);
        const q = query(queueColRef);

        const unsubscribe = onSnapshot(q, (snapshot) => {
            const allQueueItems = snapshot.docs
                .map(doc => ({ id: doc.id, ...doc.data() }))
                .filter(item => item.status === 'waiting' || item.status === 'notified')
                .sort((a, b) => a.timestamp.toDate().getTime() - b.timestamp.toDate().getTime()); // Sort by timestamp

            const userIndex = allQueueItems.findIndex(item => item.userId === userId);
            if (userIndex !== -1) {
                setQueuePosition(userIndex + 1);
            } else {
                setQueuePosition(null); // User is no longer in queue or order completed
            }
        }, (error) => {
            console.error("Error fetching queue for position:", error);
        });

        return () => unsubscribe();
    }, [db, userId, appId]);

    return (
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            <h2 className="text-3xl font-bold text-gray-800 mb-6">Fila Virtual</h2>
            {queueItem.status === 'waiting' && queuePosition !== null && (
                <>
                    <p className="text-xl text-gray-700 mb-4">
                        Estás en la fila. Tu posición actual: <span className="font-extrabold text-blue-600 text-4xl">{queuePosition}</span>
                    </p>
                    <p className="text-gray-600">Por favor, espera tu turno. Te notificaremos cuando tu pedido esté listo para recoger.</p>
                </>
            )}
            {queueItem.status === 'notified' && (
                <>
                    <p className="text-2xl font-bold text-green-600 mb-4">
                        ¡Es tu turno para recoger tu pedido!
                    </p>
                    {countdown !== null && (
                        <p className="text-xl text-gray-800 mb-6">
                            Tiempo restante: <span className="font-extrabold text-red-600 text-4xl">{formatTime(countdown)}</span>
                        </p>
                    )}
                    <p className="text-gray-700">Dirígete al casino para retirar y pagar tu pedido.</p>
                </>
            )}
            {queueItem.status === 'missed' && (
                <p className="text-2xl font-bold text-red-600 mb-4">
                    Tu tiempo para recoger el pedido ha expirado. Por favor, contacta al personal del casino.
                </p>
            )}
            {queueItem.status === 'completed' && (
                <p className="text-2xl font-bold text-blue-600 mb-4">
                    ¡Tu pedido ha sido completado! Gracias por tu compra.
                </p>
            )}

            {showMessageModal && (
                <MessageModal message={messageContent} onClose={onCloseMessage} />
            )}
        </div>
    );
};

const AdminDashboard = () => {
    const { db, handleLogout } = useContext(AppContext); // Destructure handleLogout
    const [queue, setQueue] = useState([]);
    const [message, setMessage] = useState('');
    const messageTimeoutRef = useRef(null);
    const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

    // Listen for queue updates
    useEffect(() => {
        if (!db) return;

        const queueColRef = collection(db, `artifacts/${appId}/public/data/queue`);
        const q = query(queueColRef);

        const unsubscribe = onSnapshot(q, (snapshot) => {
            const queueData = snapshot.docs
                .map(doc => ({ id: doc.id, ...doc.data() }))
                .filter(item => item.status === 'waiting' || item.status === 'notified') // Only show active queue items
                .sort((a, b) => a.timestamp.toDate().getTime() - b.timestamp.toDate().getTime()); // Sort by timestamp
            setQueue(queueData);
        }, (error) => {
            console.error("Error fetching admin queue:", error);
        });

        return () => unsubscribe();
    }, [db, appId]);

    const showTemporaryMessage = (msg) => {
        setMessage(msg);
        if (messageTimeoutRef.current) {
            clearTimeout(messageTimeoutRef.current);
        }
        messageTimeoutRef.current = setTimeout(() => {
            setMessage('');
        }, 3000);
    };

    const handleAdvanceQueue = async () => {
        if (!db || queue.length === 0) {
            showTemporaryMessage('No hay pedidos en la fila para avanzar.');
            return;
        }

        const nextInQueue = queue[0];
        const queueItemRef = doc(db, `artifacts/${appId}/public/data/queue`, nextInQueue.id);

        try {
            // Mark the next item as 'notified'
            await updateDoc(queueItemRef, {
                status: 'notified',
                notifiedAt: new Date()
            });
            showTemporaryMessage(`Pedido de ${nextInQueue.userId} notificado.`);
        } catch (error) {
            console.error("Error advancing queue:", error);
            showTemporaryMessage("Error al avanzar la fila.");
        }
    };

    const handleMarkAsCompleted = async (queueItemId, orderId) => {
        if (!db) return;
        const queueItemRef = doc(db, `artifacts/${appId}/public/data/queue`, queueItemId);
        const orderRef = doc(db, `artifacts/${appId}/public/data/orders`, orderId);

        try {
            await updateDoc(queueItemRef, { status: 'completed' });
            await updateDoc(orderRef, { status: 'completed' });
            showTemporaryMessage('Pedido marcado como completado.');
        } catch (error) {
            console.error("Error marking order as completed:", error);
            showTemporaryMessage("Error al marcar como completado.");
        }
    };

    const handleMarkAsMissed = async (queueItemId, orderId) => {
        if (!db) return;
        const queueItemRef = doc(db, `artifacts/${appId}/public/data/queue`, queueItemId);
        const orderRef = doc(db, `artifacts/${appId}/public/data/orders`, orderId);

        try {
            await updateDoc(queueItemRef, { status: 'missed' });
            await updateDoc(orderRef, { status: 'cancelled' }); // Or a specific 'missed' status
            showTemporaryMessage('Pedido marcado como perdido.');
        } catch (error) {
            console.error("Error marking order as missed:", error);
            showTemporaryMessage("Error al marcar como perdido.");
        }
    };

    return (
        <div className="space-y-8">
            {message && (
                <div className="fixed top-4 right-4 bg-blue-500 text-white px-4 py-2 rounded-md shadow-lg z-50">
                    {message}
                </div>
            )}
            <div className="flex justify-end mb-4">
                <button
                    onClick={handleLogout}
                    className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-150 ease-in-out"
                >
                    Cerrar Sesión
                </button>
            </div>
            <ProductList isAdmin={true} />

            <div className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-3xl font-bold text-gray-800 mb-6 text-center">Gestión de Fila Virtual</h2>
                <div className="flex justify-center mb-6">
                    <button
                        onClick={handleAdvanceQueue}
                        disabled={queue.length === 0}
                        className={`py-3 px-6 rounded-lg font-bold text-white shadow-lg transition duration-150 ease-in-out transform hover:scale-105 ${
                            queue.length === 0 ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'
                        }`}
                    >
                        Avanzar Fila
                    </button>
                </div>

                <h3 className="text-2xl font-semibold text-gray-800 mb-4">Pedidos en Fila ({queue.length})</h3>
                {queue.length === 0 ? (
                    <p className="text-gray-600 text-center">No hay pedidos en la fila actualmente.</p>
                ) : (
                    <ul className="space-y-4">
                        {queue.map((item, index) => (
                            <li key={item.id} className="bg-gray-50 p-4 rounded-md shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center">
                                <div>
                                    <p className="text-lg font-medium text-gray-900">
                                        Posición {index + 1}: Pedido de <span className="font-mono text-blue-700">{item.userId}</span>
                                    </p>
                                    <p className="text-sm text-gray-600">
                                        Estado: <span className={`font-semibold ${item.status === 'notified' ? 'text-green-600' : 'text-orange-600'}`}>
                                            {item.status === 'waiting' ? 'Esperando' : 'Notificado'}
                                        </span>
                                    </p>
                                    {item.notifiedAt && (
                                        <p className="text-sm text-gray-600">
                                            Notificado: {new Date(item.notifiedAt.toDate()).toLocaleTimeString()}
                                        </p>
                                    )}
                                </div>
                                <div className="mt-3 sm:mt-0 flex space-x-2">
                                    <button
                                        onClick={() => handleMarkAsCompleted(item.id, item.orderId)}
                                        className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-md shadow-sm transition duration-150 ease-in-out"
                                    >
                                        Completado
                                    </button>
                                    <button
                                        onClick={() => handleMarkAsMissed(item.id, item.orderId)}
                                        className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-md shadow-sm transition duration-150 ease-in-out"
                                    >
                                        Perdido
                                    </button>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
};

const MessageModal = ({ message, onClose }) => {
    return (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-white p-8 rounded-lg shadow-xl max-w-sm w-full text-center">
                <h3 className="text-2xl font-bold text-gray-800 mb-4">Notificación</h3>
                <p className="text-lg text-gray-700 mb-6">{message}</p>
                <button
                    onClick={onClose}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg shadow-md transition duration-150 ease-in-out"
                >
                    Entendido
                </button>
            </div>
        </div>
    );
};

export default App;
