-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Mar 13, 2026 at 03:20 PM
-- Server version: 9.4.0
-- PHP Version: 8.1.33

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";
SET SESSION sql_require_primary_key = 0;


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `hybstockadvisor`
--

-- --------------------------------------------------------

--
-- Table structure for table `notifications`
--

CREATE TABLE `notifications` (
  `id` int NOT NULL,
  `user_id` int NOT NULL,
  `title` varchar(100) NOT NULL,
  `message` text NOT NULL,
  `is_read` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `password_resets`
--

CREATE TABLE `password_resets` (
  `id` int NOT NULL,
  `email` varchar(150) NOT NULL,
  `otp` varchar(6) NOT NULL,
  `reset_token` varchar(100) DEFAULT NULL,
  `expires_at` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `password_resets`
--

INSERT INTO `password_resets` (`id`, `email`, `otp`, `reset_token`, `expires_at`) VALUES
(2, 'user1@gmail.com', '984191', NULL, '2026-03-11 10:33:13'),
(3, 'ebomofiyin@outlook.com', '726405', NULL, '2026-03-11 11:29:07');

-- --------------------------------------------------------

--
-- Table structure for table `portfolios`
--

CREATE TABLE `portfolios` (
  `id` int NOT NULL,
  `user_id` int NOT NULL,
  `ticker` varchar(20) NOT NULL,
  `quantity` decimal(10,2) NOT NULL,
  `average_buy_price` decimal(10,2) NOT NULL,
  `added_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `portfolios`
--

INSERT INTO `portfolios` (`id`, `user_id`, `ticker`, `quantity`, `average_buy_price`, `added_at`) VALUES
(1, 1, 'ARADEL', 1.70, 1300.40, '2026-03-06 14:01:55'),
(2, 1, 'BUACEMENT', 2.40, 225.00, '2026-03-06 14:01:57'),
(3, 1, 'UBA', 3.60, 47.65, '2026-03-06 14:01:58'),
(4, 1, 'NAHCO', 1.70, 170.00, '2026-03-06 14:02:35'),
(6, 1, 'ZENITHBANK', 44.20, 93.00, '2026-03-06 15:11:47'),
(12, 1, 'STANBIC', 8.60, 133.00, '2026-03-06 15:30:04'),
(13, 4, 'BUACEMENT', 8.70, 225.00, '2026-03-06 15:31:07'),
(14, 4, 'NAHCO', 2.60, 170.00, '2026-03-06 15:31:07'),
(15, 1, 'GUINNESS', 22.00, 344.29, '2026-03-10 09:23:06'),
(19, 1, 'WEMABANK', 12.00, 25.55, '2026-03-11 09:57:09'),
(20, 1, 'UNILEVER', 12.00, 94.00, '2026-03-11 09:57:58'),
(22, 1, 'AIRTELAFRI', 25.00, 2270.00, '2026-03-11 15:24:38'),
(23, 8, 'ABBEYBDS', 45.00, 7.09, '2026-03-12 12:12:46'),
(24, 8, 'ACCESSCORP', 80.00, 22.41, '2026-03-12 12:12:50'),
(25, 8, 'AIICO', 3.00, 3.12, '2026-03-12 12:12:51'),
(26, 8, 'ARADEL', 30.00, 468.57, '2026-03-12 12:12:51'),
(27, 8, 'CHAMS', 4200.00, 2.33, '2026-03-12 12:12:51'),
(28, 8, 'DANGCEM', 148.00, 524.21, '2026-03-12 12:12:51'),
(29, 8, 'JAIZBANK', 3.00, 3.79, '2026-03-12 12:12:51'),
(30, 8, 'JOHNHOLT', 805.00, 7.86, '2026-03-12 12:12:51'),
(31, 8, 'MTNN', 131.00, 262.78, '2026-03-12 12:12:51'),
(32, 8, 'NAHCO', 10.00, 80.72, '2026-03-12 12:12:51'),
(33, 8, 'NB', 7.00, 58.56, '2026-03-12 12:12:51'),
(34, 8, 'NESTLE', 6.00, 1517.90, '2026-03-12 12:12:51'),
(35, 8, 'WAPCO', 779.00, 25.67, '2026-03-12 12:12:51'),
(36, 9, 'ARADEL', 12.00, 1340.00, '2026-03-12 13:45:27');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int NOT NULL,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(150) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `risk_tolerance` varchar(50) DEFAULT 'Medium',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `first_name`, `last_name`, `username`, `email`, `password_hash`, `risk_tolerance`, `created_at`) VALUES
(1, 'Mofiyin', 'Ebo', 'mofixiu', 'ebomofiyin@outlook.com', '$2b$12$GD6fDM1Ik41XTIFZ2GzgtOceArMLLQdr66jL4vNVVQ0dmHmZfh4UO', 'High', '2026-03-05 20:20:20'),
(4, 'User', 'Test', 'motion', 'user1@gmail.com', '$2b$12$g1ZMWjWyCt5MZ771OqsNzu/laOkx5IN07yb9xrpmNaIpnmg5Mi8oW', 'High', '2026-03-06 15:30:42'),
(8, 'Mofiyinfoluwa', 'Ebo', 'mofi', 'mofiyinebo@gmail.com', '$2b$12$qe0apPOZnBMlKostaJiCfuxj2SnuuPt5nfcZ0BmkXlNEVluRa7ti.', 'High', '2026-03-12 12:08:00'),
(9, 'Victor', 'Ogah', 'itodo', 'ogah@gmail.com', '$2b$12$p4W7QonzUCp4MZ5NUR0E2OuBKy/.W6BV7u3y32w/rwTAtisBOf/xm', 'High', '2026-03-12 13:44:58');

-- --------------------------------------------------------

--
-- Table structure for table `watchlists`
--

CREATE TABLE `watchlists` (
  `id` int NOT NULL,
  `user_id` int NOT NULL,
  `ticker` varchar(20) NOT NULL,
  `added_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `watchlists`
--

INSERT INTO `watchlists` (`id`, `user_id`, `ticker`, `added_at`) VALUES
(2, 1, 'FIRSTHOLDCO', '2026-03-06 14:02:44'),
(3, 1, 'WEMABANK', '2026-03-06 14:02:48'),
(5, 4, 'UBA', '2026-03-06 15:31:23'),
(6, 1, 'UBA', '2026-03-11 09:56:58'),
(7, 1, 'GUINNESS', '2026-03-11 09:57:03'),
(9, 8, 'WEMABANK', '2026-03-12 12:15:09'),
(10, 8, 'NAHCO', '2026-03-12 12:59:57'),
(11, 9, 'BUACEMENT', '2026-03-12 13:45:47'),
(12, 9, 'STERLINGNG', '2026-03-12 13:45:49'),
(13, 8, 'FIRSTHOLDCO', '2026-03-13 15:09:38');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `notifications`
--
ALTER TABLE `notifications`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `password_resets`
--
ALTER TABLE `password_resets`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `portfolios`
--
ALTER TABLE `portfolios`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `watchlists`
--
ALTER TABLE `watchlists`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `notifications`
--
ALTER TABLE `notifications`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `password_resets`
--
ALTER TABLE `password_resets`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `portfolios`
--
ALTER TABLE `portfolios`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=38;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT for table `watchlists`
--
ALTER TABLE `watchlists`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `notifications`
--
ALTER TABLE `notifications`
  ADD CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `portfolios`
--
ALTER TABLE `portfolios`
  ADD CONSTRAINT `portfolios_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `watchlists`
--
ALTER TABLE `watchlists`
  ADD CONSTRAINT `watchlists_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
