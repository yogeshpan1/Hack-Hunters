-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Sep 12, 2026 at 08:21 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `rte_system`
--

-- --------------------------------------------------------

--
-- Table structure for table `cohorts`
--

CREATE TABLE `cohorts` (
  `cohort_id` int(11) NOT NULL,
  `programme_id` int(11) NOT NULL,
  `cohort_name` varchar(100) NOT NULL,
  `academic_year` varchar(20) DEFAULT NULL,
  `semester` varchar(20) DEFAULT NULL,
  `size` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `cohorts`
--

INSERT INTO `cohorts` (`cohort_id`, `programme_id`, `cohort_name`, `academic_year`, `semester`, `size`) VALUES
(1, 1, 'Computing Year 1', '2026', 'Semester 1', 40),
(2, 1, 'Computing Year 2', '2026', 'Semester 1', 35),
(3, 1, 'Computing Year 3', '2026', 'Semester 1', 30),
(4, 2, 'AI Year 3', '2026', 'Semester 1', 25),
(5, 3, 'Cyber Security Year 3', '2026', 'Semester 1', 28);

-- --------------------------------------------------------

--
-- Table structure for table `examination_sessions`
--

CREATE TABLE `examination_sessions` (
  `exam_id` int(11) NOT NULL,
  `module_id` int(11) NOT NULL,
  `cohort_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `time_slot_id` int(11) NOT NULL,
  `exam_date` date NOT NULL,
  `duration_minutes` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `examination_sessions`
--

INSERT INTO `examination_sessions` (`exam_id`, `module_id`, `cohort_id`, `room_id`, `time_slot_id`, `exam_date`, `duration_minutes`) VALUES
(1, 1, 3, 6, 1, '2026-12-01', 120),
(2, 2, 3, 6, 2, '2026-12-03', 120),
(3, 4, 4, 6, 5, '2026-12-05', 120);

-- --------------------------------------------------------

--
-- Table structure for table `exam_seats`
--

CREATE TABLE `exam_seats` (
  `exam_seat_id` int(11) NOT NULL,
  `exam_id` int(11) NOT NULL,
  `student_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `seat_number` varchar(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `exam_seats`
--

INSERT INTO `exam_seats` (`exam_seat_id`, `exam_id`, `student_id`, `room_id`, `seat_number`) VALUES
(1, 1, 1, 6, 'A01'),
(2, 1, 2, 6, 'A02'),
(3, 1, 3, 6, 'A03'),
(4, 1, 4, 6, 'A04');

-- --------------------------------------------------------

--
-- Table structure for table `faculty`
--

CREATE TABLE `faculty` (
  `faculty_id` int(11) NOT NULL,
  `staff_number` varchar(30) DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `email` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `faculty`
--

INSERT INTO `faculty` (`faculty_id`, `staff_number`, `name`, `email`) VALUES
(1, 'FAC001', 'John Smith', 'john.smith@islington.edu.np'),
(2, 'FAC002', 'Sarah Wilson', 'sarah.wilson@islington.edu.np'),
(3, 'FAC003', 'Michael Brown', 'michael.brown@islington.edu.np'),
(4, 'FAC004', 'David Taylor', 'david.taylor@islington.edu.np');

-- --------------------------------------------------------

--
-- Table structure for table `modules`
--

CREATE TABLE `modules` (
  `module_id` int(11) NOT NULL,
  `module_code` varchar(20) NOT NULL,
  `module_name` varchar(100) NOT NULL,
  `credits` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `modules`
--

INSERT INTO `modules` (`module_id`, `module_code`, `module_name`, `credits`) VALUES
(1, 'CS101', 'Programming', 15),
(2, 'CS102', 'Database Systems', 15),
(3, 'CS201', 'Web Development', 15),
(4, 'CS301', 'Artificial Intelligence', 15),
(5, 'CS302', 'Cyber Security', 15);

-- --------------------------------------------------------

--
-- Table structure for table `module_faculty`
--

CREATE TABLE `module_faculty` (
  `module_id` int(11) NOT NULL,
  `faculty_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `module_faculty`
--

INSERT INTO `module_faculty` (`module_id`, `faculty_id`) VALUES
(1, 1),
(2, 2),
(3, 3),
(4, 1),
(5, 4);

-- --------------------------------------------------------

--
-- Table structure for table `programmes`
--

CREATE TABLE `programmes` (
  `programme_id` int(11) NOT NULL,
  `programme_code` varchar(20) NOT NULL,
  `programme_name` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `programmes`
--

INSERT INTO `programmes` (`programme_id`, `programme_code`, `programme_name`) VALUES
(1, 'BSC-COMP', 'BSc Computing'),
(2, 'BSC-AI', 'BSc Artificial Intelligence'),
(3, 'BSC-CS', 'BSc Cyber Security');

-- --------------------------------------------------------

--
-- Table structure for table `rooms`
--

CREATE TABLE `rooms` (
  `room_id` int(11) NOT NULL,
  `room_name` varchar(50) NOT NULL,
  `building` varchar(100) DEFAULT NULL,
  `capacity` int(11) NOT NULL,
  `room_type` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `rooms`
--

INSERT INTO `rooms` (`room_id`, `room_name`, `building`, `capacity`, `room_type`) VALUES
(1, 'Room A', 'Main Building', 40, 'Classroom'),
(2, 'Room B', 'Main Building', 60, 'Classroom'),
(3, 'Room C', 'Main Building', 30, 'Classroom'),
(4, 'Lab 1', 'Technology Building', 30, 'Computer Lab'),
(5, 'Lab 2', 'Technology Building', 40, 'Computer Lab'),
(6, 'Exam Hall 1', 'Main Building', 100, 'Examination Hall'),
(7, 'Kumari Hall 1', NULL, 270, NULL),
(8, 'Kumari Hall 2', NULL, 180, NULL),
(9, 'Buckingham Palace', NULL, 90, NULL),
(10, 'Kensington Palace', NULL, 90, NULL),
(11, 'Westminster Palace', NULL, 90, NULL),
(12, 'Tridev Gurung', NULL, 100, NULL),
(13, 'Amir Khadka', NULL, 100, NULL),
(14, 'Chhitesh Lal Shrestha', NULL, 96, NULL),
(15, 'Naresh Lamgade', NULL, 88, NULL),
(16, 'Innovate Tech', NULL, 60, NULL),
(17, 'ING Skill Academy', NULL, 72, NULL),
(18, 'Vairav Tech', NULL, 72, NULL),
(19, 'Tower Bridge', NULL, 57, NULL),
(20, 'Trafalgar Square', NULL, 50, NULL),
(21, 'Piccadilly Circus', NULL, 49, NULL),
(22, 'Tower of London', NULL, 46, NULL),
(23, 'Rotash Shrestha', NULL, 48, NULL),
(24, 'Abhash Bikram Thapa', NULL, 48, NULL),
(25, 'Sujan Khadgi', NULL, 48, NULL),
(26, 'Sajiya Gurung', NULL, 48, NULL),
(27, 'Simran Bhattarai', NULL, 48, NULL),
(28, 'Samir Gautam', NULL, 48, NULL),
(29, 'Kantipur', NULL, 39, NULL),
(30, 'Patan', NULL, 40, NULL),
(31, 'Pokhara', NULL, 32, NULL),
(32, 'Lumbini', NULL, 36, NULL),
(33, 'Machapuchare', NULL, 37, NULL),
(34, 'Annapurna', NULL, 40, NULL),
(35, 'Kanchanjunga', NULL, 39, NULL),
(36, 'Sagarmatha', NULL, 34, NULL),
(37, 'mySecondTeacher', NULL, 24, NULL),
(38, 'One More Bite', NULL, 24, NULL),
(39, 'ING Arc', NULL, 24, NULL),
(40, 'ING Tech', NULL, 24, NULL),
(41, 'inRed Labs', NULL, 24, NULL),
(42, 'Prashidika Tiwari', NULL, 30, NULL),
(43, 'Sarad Paudel', NULL, 60, NULL),
(44, 'Prashraya Thapa', NULL, 30, NULL),
(45, 'Raj Bikram Shrestha', NULL, 30, NULL),
(46, 'Aayesha Nakarmi', NULL, 30, NULL),
(47, 'Ams Ghimire', NULL, 30, NULL),
(48, 'Lasata Maharjan', NULL, 30, NULL),
(49, 'Kshitiz Shrestha', NULL, 30, NULL),
(50, 'Sahas Shakya', NULL, 30, NULL),
(51, 'Aashima Chalise', NULL, 30, NULL),
(52, 'Sonik Das Mulmi', NULL, 30, NULL),
(53, 'Ronisha Shrestha', NULL, 30, NULL),
(54, 'Sheneeza Chaudhary', NULL, 30, NULL),
(55, 'Jeevan Khatiwada', NULL, 30, NULL),
(56, 'Suvan Thapa Magar', NULL, 30, NULL),
(57, 'Sushant Hona', NULL, 30, NULL),
(58, 'Lab 13', NULL, 24, NULL),
(59, 'Lab 14', NULL, 24, NULL),
(60, 'Lab 15', NULL, 24, NULL),
(61, 'Lab 16', NULL, 24, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `students`
--

CREATE TABLE `students` (
  `student_id` int(11) NOT NULL,
  `student_number` varchar(30) NOT NULL,
  `first_name` varchar(50) NOT NULL,
  `last_name` varchar(50) NOT NULL,
  `cohort_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `students`
--

INSERT INTO `students` (`student_id`, `student_number`, `first_name`, `last_name`, `cohort_id`) VALUES
(1, 'STU001', 'John', 'Doe', 3),
(2, 'STU002', 'Jane', 'Smith', 3),
(3, 'STU003', 'Alex', 'Brown', 3),
(4, 'STU004', 'Sam', 'Wilson', 3),
(5, 'STU005', 'David', 'Taylor', 4);

-- --------------------------------------------------------

--
-- Table structure for table `timetable_sessions`
--

CREATE TABLE `timetable_sessions` (
  `session_id` int(11) NOT NULL,
  `module_id` int(11) NOT NULL,
  `faculty_id` int(11) NOT NULL,
  `cohort_id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `time_slot_id` int(11) NOT NULL,
  `session_type` varchar(30) DEFAULT 'LECTURE'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `timetable_sessions`
--

INSERT INTO `timetable_sessions` (`session_id`, `module_id`, `faculty_id`, `cohort_id`, `room_id`, `time_slot_id`, `session_type`) VALUES
(1, 1, 1, 3, 1, 1, 'LECTURE'),
(2, 2, 2, 3, 2, 2, 'LECTURE'),
(3, 3, 3, 3, 4, 3, 'LAB'),
(4, 4, 1, 4, 3, 6, 'LECTURE'),
(5, 5, 4, 5, 2, 5, 'LECTURE'),
(6, 2, 2, 4, 1, 1, 'LECTURE'),
(7, 3, 1, 4, 2, 1, 'LECTURE'),
(8, 4, 4, 3, 3, 1, 'LECTURE');

-- --------------------------------------------------------

--
-- Table structure for table `time_slots`
--

CREATE TABLE `time_slots` (
  `time_slot_id` int(11) NOT NULL,
  `day_of_week` varchar(20) NOT NULL,
  `start_time` time NOT NULL,
  `end_time` time NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `time_slots`
--

INSERT INTO `time_slots` (`time_slot_id`, `day_of_week`, `start_time`, `end_time`) VALUES
(1, 'Monday', '08:00:00', '10:00:00'),
(2, 'Monday', '10:00:00', '12:00:00'),
(3, 'Monday', '13:00:00', '15:00:00'),
(4, 'Monday', '15:00:00', '17:00:00'),
(5, 'Tuesday', '08:00:00', '10:00:00'),
(6, 'Tuesday', '10:00:00', '12:00:00'),
(7, 'Tuesday', '13:00:00', '15:00:00'),
(8, 'Tuesday', '15:00:00', '17:00:00'),
(9, 'Wednesday', '08:00:00', '10:00:00'),
(10, 'Wednesday', '10:00:00', '12:00:00'),
(11, 'Wednesday', '13:00:00', '15:00:00'),
(12, 'Wednesday', '15:00:00', '17:00:00'),
(13, 'Thursday', '08:00:00', '10:00:00'),
(14, 'Thursday', '10:00:00', '12:00:00'),
(15, 'Thursday', '13:00:00', '15:00:00'),
(16, 'Thursday', '15:00:00', '17:00:00'),
(17, 'Friday', '08:00:00', '10:00:00'),
(18, 'Friday', '10:00:00', '12:00:00'),
(19, 'Friday', '13:00:00', '15:00:00'),
(20, 'Friday', '15:00:00', '17:00:00');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `cohorts`
--
ALTER TABLE `cohorts`
  ADD PRIMARY KEY (`cohort_id`),
  ADD UNIQUE KEY `cohort_name` (`cohort_name`),
  ADD KEY `programme_id` (`programme_id`);

--
-- Indexes for table `examination_sessions`
--
ALTER TABLE `examination_sessions`
  ADD PRIMARY KEY (`exam_id`),
  ADD KEY `module_id` (`module_id`),
  ADD KEY `cohort_id` (`cohort_id`),
  ADD KEY `room_id` (`room_id`),
  ADD KEY `time_slot_id` (`time_slot_id`);

--
-- Indexes for table `exam_seats`
--
ALTER TABLE `exam_seats`
  ADD PRIMARY KEY (`exam_seat_id`),
  ADD UNIQUE KEY `exam_id` (`exam_id`,`student_id`),
  ADD UNIQUE KEY `exam_id_2` (`exam_id`,`room_id`,`seat_number`),
  ADD KEY `student_id` (`student_id`),
  ADD KEY `room_id` (`room_id`);

--
-- Indexes for table `faculty`
--
ALTER TABLE `faculty`
  ADD PRIMARY KEY (`faculty_id`),
  ADD UNIQUE KEY `staff_number` (`staff_number`);

--
-- Indexes for table `modules`
--
ALTER TABLE `modules`
  ADD PRIMARY KEY (`module_id`),
  ADD UNIQUE KEY `module_code` (`module_code`);

--
-- Indexes for table `module_faculty`
--
ALTER TABLE `module_faculty`
  ADD PRIMARY KEY (`module_id`,`faculty_id`),
  ADD KEY `faculty_id` (`faculty_id`);

--
-- Indexes for table `programmes`
--
ALTER TABLE `programmes`
  ADD PRIMARY KEY (`programme_id`),
  ADD UNIQUE KEY `programme_code` (`programme_code`);

--
-- Indexes for table `rooms`
--
ALTER TABLE `rooms`
  ADD PRIMARY KEY (`room_id`),
  ADD UNIQUE KEY `room_name` (`room_name`);

--
-- Indexes for table `students`
--
ALTER TABLE `students`
  ADD PRIMARY KEY (`student_id`),
  ADD UNIQUE KEY `student_number` (`student_number`),
  ADD KEY `cohort_id` (`cohort_id`);

--
-- Indexes for table `timetable_sessions`
--
ALTER TABLE `timetable_sessions`
  ADD PRIMARY KEY (`session_id`),
  ADD KEY `module_id` (`module_id`),
  ADD KEY `faculty_id` (`faculty_id`),
  ADD KEY `cohort_id` (`cohort_id`),
  ADD KEY `room_id` (`room_id`),
  ADD KEY `time_slot_id` (`time_slot_id`);

--
-- Indexes for table `time_slots`
--
ALTER TABLE `time_slots`
  ADD PRIMARY KEY (`time_slot_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `cohorts`
--
ALTER TABLE `cohorts`
  MODIFY `cohort_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `examination_sessions`
--
ALTER TABLE `examination_sessions`
  MODIFY `exam_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `exam_seats`
--
ALTER TABLE `exam_seats`
  MODIFY `exam_seat_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `faculty`
--
ALTER TABLE `faculty`
  MODIFY `faculty_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `modules`
--
ALTER TABLE `modules`
  MODIFY `module_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `programmes`
--
ALTER TABLE `programmes`
  MODIFY `programme_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `rooms`
--
ALTER TABLE `rooms`
  MODIFY `room_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=62;

--
-- AUTO_INCREMENT for table `students`
--
ALTER TABLE `students`
  MODIFY `student_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `timetable_sessions`
--
ALTER TABLE `timetable_sessions`
  MODIFY `session_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT for table `time_slots`
--
ALTER TABLE `time_slots`
  MODIFY `time_slot_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `cohorts`
--
ALTER TABLE `cohorts`
  ADD CONSTRAINT `cohorts_ibfk_1` FOREIGN KEY (`programme_id`) REFERENCES `programmes` (`programme_id`);

--
-- Constraints for table `examination_sessions`
--
ALTER TABLE `examination_sessions`
  ADD CONSTRAINT `examination_sessions_ibfk_1` FOREIGN KEY (`module_id`) REFERENCES `modules` (`module_id`),
  ADD CONSTRAINT `examination_sessions_ibfk_2` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`cohort_id`),
  ADD CONSTRAINT `examination_sessions_ibfk_3` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`),
  ADD CONSTRAINT `examination_sessions_ibfk_4` FOREIGN KEY (`time_slot_id`) REFERENCES `time_slots` (`time_slot_id`);

--
-- Constraints for table `exam_seats`
--
ALTER TABLE `exam_seats`
  ADD CONSTRAINT `exam_seats_ibfk_1` FOREIGN KEY (`exam_id`) REFERENCES `examination_sessions` (`exam_id`),
  ADD CONSTRAINT `exam_seats_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`),
  ADD CONSTRAINT `exam_seats_ibfk_3` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`);

--
-- Constraints for table `module_faculty`
--
ALTER TABLE `module_faculty`
  ADD CONSTRAINT `module_faculty_ibfk_1` FOREIGN KEY (`module_id`) REFERENCES `modules` (`module_id`),
  ADD CONSTRAINT `module_faculty_ibfk_2` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`faculty_id`);

--
-- Constraints for table `students`
--
ALTER TABLE `students`
  ADD CONSTRAINT `students_ibfk_1` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`cohort_id`);

--
-- Constraints for table `timetable_sessions`
--
ALTER TABLE `timetable_sessions`
  ADD CONSTRAINT `timetable_sessions_ibfk_1` FOREIGN KEY (`module_id`) REFERENCES `modules` (`module_id`),
  ADD CONSTRAINT `timetable_sessions_ibfk_2` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`faculty_id`),
  ADD CONSTRAINT `timetable_sessions_ibfk_3` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`cohort_id`),
  ADD CONSTRAINT `timetable_sessions_ibfk_4` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`),
  ADD CONSTRAINT `timetable_sessions_ibfk_5` FOREIGN KEY (`time_slot_id`) REFERENCES `time_slots` (`time_slot_id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
